-- 质量策略与资格历史。应用连接须启用外键、递归触发器及规范JSON函数。
-- 迁移事务由运行器持有；禁止在此提交、关闭外键或删除历史。
CREATE TABLE policy_configs (
    policy_hash TEXT PRIMARY KEY NOT NULL
        CHECK (length(policy_hash) = 64 AND policy_hash NOT GLOB '*[^0-9a-f]*'),
    config_json TEXT NOT NULL
        CHECK (json_valid(config_json) AND json_type(config_json) = 'object')
        CHECK (json_extract(config_json, '$.canonicalization') IS 'fv-json-v1')
        CHECK (json_extract(config_json, '$.contract_version') IS 2)
        CHECK (config_json = fv_canonical_json(config_json))
        CHECK (policy_hash = fv_config_hash(config_json))
) STRICT;

CREATE TABLE quality_policies (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    policy_hash TEXT NOT NULL REFERENCES policy_configs(policy_hash)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (id, version)
) STRICT;

CREATE TABLE qualification_versions (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    policy_hash TEXT NOT NULL REFERENCES policy_configs(policy_hash)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    scope_json TEXT NOT NULL
        CHECK (json_valid(scope_json) AND json_type(scope_json) = 'object')
        CHECK (scope_json = fv_canonical_json(scope_json)),
    change_triggers_json TEXT NOT NULL
        CHECK (json_valid(change_triggers_json) AND json_type(change_triggers_json) = 'array')
        CHECK (json_array_length(change_triggers_json) > 0)
        CHECK (change_triggers_json = fv_canonical_json(change_triggers_json)),
    created_at TEXT NOT NULL,
    PRIMARY KEY (id, version),
    UNIQUE (id, version, policy_hash)
) STRICT;

CREATE TABLE qualification_events (
    server_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    qualification_id TEXT NOT NULL,
    qualification_version INTEGER NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    status TEXT NOT NULL CHECK (status IN ('draft', 'evaluating', 'active', 'suspended', 'revoked')),
    revocation_sequence INTEGER NOT NULL CHECK (revocation_sequence >= 0),
    dataset_sha256 TEXT CHECK (dataset_sha256 IS NULL OR
        (length(dataset_sha256) = 64 AND dataset_sha256 NOT GLOB '*[^0-9a-f]*')),
    report_sha256 TEXT CHECK (report_sha256 IS NULL OR
        (length(report_sha256) = 64 AND report_sha256 NOT GLOB '*[^0-9a-f]*')),
    issuer_id TEXT,
    issued_at TEXT,
    reason TEXT NOT NULL CHECK (length(reason) > 0),
    created_at TEXT NOT NULL,
    UNIQUE (qualification_id, qualification_version, revision),
    FOREIGN KEY (qualification_id, qualification_version)
        REFERENCES qualification_versions(id, version) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (status IN ('draft', 'evaluating') OR
        (dataset_sha256 IS NOT NULL AND report_sha256 IS NOT NULL
         AND issuer_id IS NOT NULL AND length(issuer_id) > 0
         AND issued_at IS NOT NULL AND length(issued_at) > 0)),
    CHECK ((status IN ('suspended', 'revoked') AND revocation_sequence > 0)
        OR (status IN ('draft', 'evaluating', 'active') AND revocation_sequence = 0))
) STRICT;

CREATE VIEW current_qualifications AS
SELECT v.id, v.version, v.policy_hash, v.scope_json, v.change_triggers_json,
       v.created_at, e.revision, e.status, e.revocation_sequence,
       e.dataset_sha256, e.report_sha256, e.issuer_id, e.issued_at,
       e.server_sequence
FROM qualification_versions AS v
JOIN qualification_events AS e
  ON e.qualification_id = v.id AND e.qualification_version = v.version
WHERE e.revision = (
    SELECT max(previous.revision) FROM qualification_events AS previous
    WHERE previous.qualification_id = v.id AND previous.qualification_version = v.version
);

CREATE TABLE active_qualifications (
    policy_hash TEXT PRIMARY KEY NOT NULL,
    qualification_id TEXT NOT NULL,
    qualification_version INTEGER NOT NULL,
    event_revision INTEGER NOT NULL,
    FOREIGN KEY (qualification_id, qualification_version, policy_hash)
        REFERENCES qualification_versions(id, version, policy_hash)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (qualification_id, qualification_version, event_revision)
        REFERENCES qualification_events(qualification_id, qualification_version, revision)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TRIGGER qualification_transition BEFORE INSERT ON qualification_events
BEGIN
    SELECT RAISE(ABORT, '资格首条事件必须为草稿')
    WHERE NOT EXISTS (
        SELECT 1 FROM qualification_events
        WHERE qualification_id = NEW.qualification_id AND qualification_version = NEW.qualification_version
    ) AND (NEW.revision != 1 OR NEW.status != 'draft' OR NEW.revocation_sequence != 0);

    SELECT RAISE(ABORT, '资格版本或状态转换无效')
    FROM current_qualifications AS current
    WHERE current.id = NEW.qualification_id AND current.version = NEW.qualification_version
      AND (NEW.revision != current.revision + 1
        OR NOT ((current.status = 'draft' AND NEW.status = 'evaluating')
            OR (current.status = 'evaluating' AND NEW.status IN ('evaluating', 'active'))
            OR (current.status = 'active' AND NEW.status IN ('suspended', 'revoked'))
            OR (current.status = 'suspended' AND NEW.status = 'revoked'))
        OR NEW.revocation_sequence != current.revocation_sequence
            + CASE WHEN NEW.status IN ('suspended', 'revoked') THEN 1 ELSE 0 END);

    SELECT RAISE(ABORT, '已签发资格不得更换报告或签发者')
    FROM current_qualifications AS current
    WHERE current.id = NEW.qualification_id AND current.version = NEW.qualification_version
      AND current.status IN ('active', 'suspended', 'revoked')
      AND (NEW.dataset_sha256 IS NOT current.dataset_sha256
        OR NEW.report_sha256 IS NOT current.report_sha256
        OR NEW.issuer_id IS NOT current.issuer_id
        OR NEW.issued_at IS NOT current.issued_at);
END;

CREATE TRIGGER active_qualification_insert BEFORE INSERT ON active_qualifications
BEGIN
    SELECT RAISE(ABORT, '只能选择当前有效资格') WHERE NOT EXISTS (
        SELECT 1 FROM current_qualifications
        WHERE id = NEW.qualification_id AND version = NEW.qualification_version
            AND policy_hash = NEW.policy_hash AND revision = NEW.event_revision AND status = 'active'
    );
END;

CREATE TRIGGER active_qualification_update BEFORE UPDATE ON active_qualifications
BEGIN
    SELECT RAISE(ABORT, '只能选择当前有效资格') WHERE NOT EXISTS (
        SELECT 1 FROM current_qualifications
        WHERE id = NEW.qualification_id AND version = NEW.qualification_version
            AND policy_hash = NEW.policy_hash AND revision = NEW.event_revision AND status = 'active'
    );
END;

CREATE TRIGGER deselect_invalid_qualification AFTER INSERT ON qualification_events
WHEN NEW.status IN ('suspended', 'revoked')
BEGIN
    DELETE FROM active_qualifications
    WHERE qualification_id = NEW.qualification_id AND qualification_version = NEW.qualification_version;
END;

CREATE TRIGGER policy_config_no_update BEFORE UPDATE ON policy_configs
BEGIN SELECT RAISE(ABORT, '策略配置不可覆盖'); END;
CREATE TRIGGER policy_config_no_delete BEFORE DELETE ON policy_configs
BEGIN SELECT RAISE(ABORT, '策略配置不可删除'); END;
CREATE TRIGGER quality_policy_no_update BEFORE UPDATE ON quality_policies
BEGIN SELECT RAISE(ABORT, '策略版本不可覆盖'); END;
CREATE TRIGGER quality_policy_no_delete BEFORE DELETE ON quality_policies
BEGIN SELECT RAISE(ABORT, '策略版本不可删除'); END;
CREATE TRIGGER qualification_version_no_update BEFORE UPDATE ON qualification_versions
BEGIN SELECT RAISE(ABORT, '资格定义不可覆盖'); END;
CREATE TRIGGER qualification_version_no_delete BEFORE DELETE ON qualification_versions
BEGIN SELECT RAISE(ABORT, '资格定义不可删除'); END;
CREATE TRIGGER qualification_event_no_update BEFORE UPDATE ON qualification_events
BEGIN SELECT RAISE(ABORT, '资格事件只可追加'); END;
CREATE TRIGGER qualification_event_no_delete BEFORE DELETE ON qualification_events
BEGIN SELECT RAISE(ABORT, '资格事件只可追加'); END;
