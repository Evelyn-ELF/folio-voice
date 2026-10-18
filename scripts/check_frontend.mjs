// 使用TypeScript语法树与模块解析，检查Web和共享契约的实际依赖。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = fs.realpathSync(path.resolve(process.argv[2] === '--root' ? process.argv[3] : fileURLToPath(new URL('..', import.meta.url))));
const errors = [];
const files = [];
function walk(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (['node_modules', 'dist', '__pycache__'].includes(entry.name)) continue;
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (/\.(?:[cm]?[jt]sx?)$/.test(file)) files.push(file);
  }
}
for (const name of ['apps', 'packages', 'workers']) walk(path.join(root, name));
const graph = new Map(files.map(file => [file, new Set()]));
const relative = file => path.relative(root, file).split(path.sep).join('/');
const options = { moduleResolution: ts.ModuleResolutionKind.Bundler, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX };
for (const file of files) {
  const name = relative(file);
  const web = name.startsWith('apps/web/');
  const contract = name.startsWith('packages/contracts/');
  if (!web && !contract) errors.push(`${name}：未分配前端依赖规则`);
  const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
  function dependency(specifier) {
    if (!specifier.startsWith('.')) {
      const allowed = name === 'apps/web/vite.config.ts' ? ['vite'] : ['react', 'react-dom', 'react-dom/client', 'react/jsx-runtime'];
      if (!web || !allowed.includes(specifier)) errors.push(`${name}：禁止外部依赖${specifier}`);
      return;
    }
    let target = ts.resolveModuleName(specifier, file, options, ts.sys).resolvedModule?.resolvedFileName;
    if (!target && /\.css$/.test(specifier) && fs.existsSync(path.resolve(path.dirname(file), specifier))) target = path.resolve(path.dirname(file), specifier);
    if (!target) { errors.push(`${name}：依赖不存在${specifier}`); return; }
    target = fs.realpathSync(target);
    const destination = relative(target);
    if (!(web && (destination.startsWith('apps/web/') || destination.startsWith('packages/contracts/'))) && !(contract && destination.startsWith('packages/contracts/'))) errors.push(`${name}：禁止跨层依赖${destination}`);
    if (graph.has(target)) graph.get(file).add(target);
  }
  function visit(node) {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier) {
      if (ts.isStringLiteralLike(node.moduleSpecifier)) dependency(node.moduleSpecifier.text);
    }
    if (ts.isImportEqualsDeclaration(node) || (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && ['require', 'eval', 'Function'].includes(node.expression.text))) errors.push(`${name}：禁止动态依赖或代码加载`);
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
      if (node.arguments.length !== 1 || !ts.isStringLiteralLike(node.arguments[0])) errors.push(`${name}：禁止计算动态依赖`);
      else dependency(node.arguments[0].text);
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  for (const reference of source.referencedFiles) dependency(reference.fileName.startsWith('.') ? reference.fileName : './' + reference.fileName);
}
const done = new Set();
const stack = [];
function visit(file) {
  if (stack.includes(file)) { errors.push('循环依赖：' + [...stack.slice(stack.indexOf(file)), file].map(relative).join(' → ')); return; }
  if (done.has(file)) return;
  stack.push(file);
  for (const target of graph.get(file)) visit(target);
  stack.pop();
  done.add(file);
}
for (const file of files) visit(file);
console.log(JSON.stringify({ 文件数: files.length, 错误: errors }));
process.exitCode = errors.length ? 1 : 0;
