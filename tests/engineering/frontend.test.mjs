import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const script = fileURLToPath(new URL('../../scripts/check_frontend.mjs', import.meta.url));
async function run(files, expected) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'folio-boundary-'));
  try {
    for (const [name, content] of Object.entries(files)) {
      const file = path.join(root, name);
      await mkdir(path.dirname(file), { recursive: true });
      await writeFile(file, content);
    }
    const result = spawnSync(process.execPath, [script, '--root', root], { encoding: 'utf8' });
    assert.equal(result.status, expected, result.stdout + result.stderr);
    return JSON.parse(result.stdout);
  } finally { await rm(root, { recursive: true, force: true }); }
}
test('Web可以引用契约及组件', async () => {
  await run({ 'apps/web/src/a.ts': "import type { A } from '../../../packages/contracts/generated'", 'packages/contracts/generated.ts': 'export type A = string' }, 0);
});
test('相对导入不能穿入核心或执行器', async () => {
  for (const name of ['core', 'adapters']) {
    await run({ 'apps/web/src/a.ts': `import '../../../packages/${name}/x'`, [`packages/${name}/x.ts`]: '' }, 1);
  }
});
test('导出与动态导入同样检查', async () => {
  for (const source of ["export * from '../../../packages/core/x'", "import('../../../packages/core/x')", 'import(target)', "require('node:fs')", "import fs from 'node:fs'"]) {
    await run({ 'apps/web/src/a.ts': source, 'packages/core/x.ts': '' }, 1);
  }
});
test('循环引用被拦截', async () => {
  const result = await run({ 'apps/web/src/a.ts': "export * from './b'", 'apps/web/src/b.ts': "import './a'" }, 1);
  assert.match(JSON.stringify(result), /循环/);
});
test('缺失模块及契约反向引用被拦截', async () => {
  await run({ 'apps/web/src/a.ts': "import './missing'" }, 1);
  await run({ 'packages/contracts/generated.ts': "import '../../apps/web/src/a'", 'apps/web/src/a.ts': '' }, 1);
});
