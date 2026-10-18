"""应用独占的SQLite连接与事务迁移；不实现产品API或资格授权。"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from packages.core.canonical import canonical_json, configuration_hash, parse_json

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    sha256: str


def _configure(connection: sqlite3.Connection) -> None:
    if connection.in_transaction:
        raise ValueError("迁移不能嵌入已有事务")
    if connection.isolation_level is not None:
        raise ValueError("迁移连接须使用显式事务模式")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA recursive_triggers = ON")
    for pragma in ("foreign_keys", "recursive_triggers"):
        if connection.execute(f"PRAGMA {pragma}").fetchone()[0] != 1:
            raise RuntimeError("SQLite连接未启用必要约束")
    connection.create_function(
        "fv_canonical_json",
        1,
        lambda source: canonical_json(parse_json(source)).decode("utf-8"),
        deterministic=True,
    )
    connection.create_function(
        "fv_config_hash",
        1,
        lambda source: configuration_hash(parse_json(source)),
        deterministic=True,
    )


def connect(path: str | Path) -> sqlite3.Connection:
    """每个应用连接都启用并验证外键，不接收模型提供的数据库路径。"""
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        _configure(connection)
    except BaseException:
        connection.close()
        raise
    return connection


def _load(directory: Path) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = re.fullmatch(r"(\d{4})_[a-z][a-z0-9_]*\.sql", path.name)
        if not match or int(match[1]) != len(migrations) + 1:
            raise ValueError("迁移版本必须从0001连续排列且名称有效")
        source = path.read_bytes()
        migrations.append(
            Migration(
                int(match[1]),
                path.name,
                source.decode("utf-8"),
                hashlib.sha256(source).hexdigest(),
            )
        )
    if not migrations:
        raise ValueError("没有可用迁移版本，拒绝初始化或降级")
    return migrations


def _statements(source: str) -> Iterator[str]:
    # complete_statement处理字符串、注释和触发器内部的分号。
    buffer = ""
    for char in source:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    # 允许尾部注释；缺分号的真正语句明确拒绝，不静默丢弃。
    tail = re.sub(r"--[^\n]*|/\*.*?\*/", "", buffer, flags=re.S).strip()
    if tail:
        raise ValueError("迁移语句未以分号结束")


def _authorize_migration(
    action: int,
    first: str | None,
    second: str | None,
    database: str | None,
    origin: str | None,
) -> int:
    if action in (
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def migrate(connection: sqlite3.Connection, directory: Path = MIGRATIONS) -> None:
    """验证已应用迁移，再原子应用全部待执行迁移；失败回退DDL和版本账。"""
    migrations = _load(directory)
    _configure(connection)
    connection.execute("BEGIN IMMEDIATE")
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables and "schema_migrations" not in tables:
            raise ValueError("非空数据库没有迁移版本账，拒绝接管")
        connection.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY CHECK (version > 0),
            name TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        ) STRICT""")
        applied = connection.execute(
            "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
        ).fetchall()
        if len(applied) > len(migrations):
            raise ValueError("数据库版本高于本应用，须使用匹配版本或升级前备份")
        for expected, actual in zip(migrations, applied):
            if (expected.version, expected.name, expected.sha256) != actual:
                raise ValueError("已应用迁移版本、名称或散列不一致")
        for migration in migrations[len(applied) :]:
            statements = list(_statements(migration.sql))
            connection.set_authorizer(_authorize_migration)
            try:
                for statement in statements:
                    connection.execute(statement)
            finally:
                connection.set_authorizer(None)
            connection.execute(
                "INSERT INTO schema_migrations(version, name, sha256) VALUES (?, ?, ?)",
                (migration.version, migration.name, migration.sha256),
            )
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("迁移后的外键检查失败")
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
