#!/usr/bin/env node
/** Enforce frontend transport boundaries with the TypeScript and Vue parsers. */

import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const FRONTEND_ROOT = path.join(PROJECT_ROOT, "src/frontend");
const DEFAULT_FRONTEND_SRC = path.join(FRONTEND_ROOT, "src");
const frontendRequire = createRequire(path.join(FRONTEND_ROOT, "package.json"));
const ts = frontendRequire("typescript");
const { parse: parseVueSfc } = frontendRequire("@vue/compiler-sfc");

const SOURCE_SUFFIXES = new Set([".cjs", ".cts", ".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx", ".vue"]);
const IGNORED_DIRS = new Set(["node_modules", "dist", ".vite", "coverage"]);
const TRANSPORT_GLOBALS = new Set(["fetch", "EventSource", "XMLHttpRequest"]);
const GLOBAL_OBJECTS = new Set(["globalThis", "self", "window"]);

function parseArgs(argv) {
  let frontendSrc = DEFAULT_FRONTEND_SRC;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] !== "--frontend-src" || !argv[index + 1]) {
      throw new Error(`unknown or incomplete argument: ${argv[index]}`);
    }
    frontendSrc = path.resolve(argv[index + 1]);
    index += 1;
  }
  return { frontendSrc, apiRoot: path.join(frontendSrc, "api") };
}

function isUnder(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

function iterSourceFiles(root) {
  if (!fs.existsSync(root)) {
    throw new Error(`frontend source directory does not exist: ${root}`);
  }

  const files = [];
  function visit(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (IGNORED_DIRS.has(entry.name)) continue;
      const candidate = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(candidate);
      else if (entry.isFile() && SOURCE_SUFFIXES.has(path.extname(entry.name))) files.push(candidate);
    }
  }
  visit(root);
  return files.sort();
}

function scriptKind(filename, lang = "") {
  const normalized = lang.toLowerCase() || path.extname(filename).slice(1).toLowerCase();
  if (normalized === "tsx") return ts.ScriptKind.TSX;
  if (normalized === "jsx") return ts.ScriptKind.JSX;
  if (["js", "mjs", "cjs"].includes(normalized)) return ts.ScriptKind.JS;
  return ts.ScriptKind.TS;
}

function unwrapExpression(node) {
  let current = node;
  while (
    ts.isParenthesizedExpression(current) ||
    ts.isAsExpression(current) ||
    ts.isTypeAssertionExpression(current) ||
    ts.isNonNullExpression(current) ||
    ts.isSatisfiesExpression(current)
  ) {
    current = current.expression;
  }
  return current;
}

function staticString(node) {
  const value = unwrapExpression(node);
  if (ts.isStringLiteral(value) || ts.isNoSubstitutionTemplateLiteral(value)) return value.text;
  return null;
}

function staticPropertyName(node) {
  if (ts.isIdentifier(node) || ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isComputedPropertyName(node)) return staticString(node.expression);
  return null;
}

function memberParts(node) {
  const expression = unwrapExpression(node);
  if (ts.isPropertyAccessExpression(expression)) {
    return { object: unwrapExpression(expression.expression), property: expression.name.text };
  }
  if (ts.isElementAccessExpression(expression) && expression.argumentExpression) {
    return { object: unwrapExpression(expression.expression), property: staticString(expression.argumentExpression) };
  }
  return null;
}

function globalTransportName(node) {
  const expression = unwrapExpression(node);
  if (ts.isIdentifier(expression) && TRANSPORT_GLOBALS.has(expression.text)) return expression.text;

  const member = memberParts(expression);
  if (
    member &&
    member.property &&
    TRANSPORT_GLOBALS.has(member.property) &&
    ts.isIdentifier(member.object) &&
    GLOBAL_OBJECTS.has(member.object.text)
  ) {
    return member.property;
  }
  return null;
}

function isTypePosition(node) {
  let current = node;
  while (current.parent) {
    if (ts.isTypeNode(current.parent)) return true;
    if (ts.isExpression(current.parent) || ts.isStatement(current.parent) || ts.isSourceFile(current.parent)) return false;
    current = current.parent;
  }
  return false;
}

function isDeclarationOrPropertyName(node) {
  const parent = node.parent;
  if (!parent) return false;
  if (
    (ts.isVariableDeclaration(parent) ||
      ts.isParameter(parent) ||
      ts.isFunctionDeclaration(parent) ||
      ts.isFunctionExpression(parent) ||
      ts.isClassDeclaration(parent) ||
      ts.isClassExpression(parent) ||
      ts.isBindingElement(parent) ||
      ts.isImportClause(parent) ||
      ts.isImportSpecifier(parent) ||
      ts.isNamespaceImport(parent)) &&
    parent.name === node
  ) {
    return true;
  }
  if (
    (ts.isPropertyAssignment(parent) ||
      ts.isPropertyDeclaration(parent) ||
      ts.isPropertySignature(parent) ||
      ts.isMethodDeclaration(parent) ||
      ts.isMethodSignature(parent) ||
      ts.isGetAccessorDeclaration(parent) ||
      ts.isSetAccessorDeclaration(parent)) &&
    parent.name === node
  ) {
    return true;
  }
  return ts.isPropertyAccessExpression(parent) && parent.name === node;
}

function axiosModule(node) {
  const value = staticString(node);
  return value !== null && (value === "axios" || value.startsWith("axios/"));
}

function bindingReadsGlobalTransport(name, initializer) {
  if (!ts.isObjectBindingPattern(name)) return false;
  const source = unwrapExpression(initializer);
  if (!ts.isIdentifier(source) || !GLOBAL_OBJECTS.has(source.text)) return false;
  return name.elements.some((element) => {
    const property = element.propertyName
      ? staticPropertyName(element.propertyName)
      : ts.isIdentifier(element.name)
        ? element.name.text
        : null;
    return property !== null && TRANSPORT_GLOBALS.has(property);
  });
}

function assignmentIsAxiosStream(node) {
  if (ts.isPropertyAssignment(node)) {
    const property = staticPropertyName(node.name);
    return property === "responseType" && staticString(node.initializer) === "stream";
  }
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
    const member = memberParts(node.left);
    return member?.property === "responseType" && staticString(node.right) === "stream";
  }
  return false;
}

function scanScript({ filename, source, lang = "", lineOffset = 0, allowHttp }) {
  const sourceFile = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, scriptKind(filename, lang));
  const violations = [];
  const seen = new Set();

  function add(node, message) {
    const localLine = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
    const line = localLine + lineOffset;
    const key = `${line}:${message}`;
    if (!seen.has(key)) {
      seen.add(key);
      violations.push({ path: filename, line, message });
    }
  }

  for (const diagnostic of sourceFile.parseDiagnostics ?? []) {
    const start = diagnostic.start ?? 0;
    const localLine = sourceFile.getLineAndCharacterOfPosition(start).line + 1;
    const message = ts.flattenDiagnosticMessageText(diagnostic.messageText, " ");
    violations.push({ path: filename, line: localLine + lineOffset, message: `cannot parse frontend source: ${message}` });
  }

  function visit(node) {
    if (!allowHttp) {
      if (
        (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
        node.moduleSpecifier &&
        axiosModule(node.moduleSpecifier)
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      } else if (
        ts.isImportEqualsDeclaration(node) &&
        ts.isExternalModuleReference(node.moduleReference) &&
        node.moduleReference.expression &&
        axiosModule(node.moduleReference.expression)
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      } else if (
        ts.isCallExpression(node) &&
        (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(node.expression) && node.expression.text === "require")) &&
        node.arguments[0] &&
        axiosModule(node.arguments[0])
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      }

      if (
        (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) &&
        globalTransportName(node)
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      } else if (
        ts.isIdentifier(node) &&
        TRANSPORT_GLOBALS.has(node.text) &&
        !isDeclarationOrPropertyName(node) &&
        !isTypePosition(node)
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      } else if (
        ts.isVariableDeclaration(node) &&
        node.initializer &&
        bindingReadsGlobalTransport(node.name, node.initializer)
      ) {
        add(node, "HTTP clients must be used through src/frontend/src/api");
      }
    }

    if (assignmentIsAxiosStream(node)) {
      add(
        node,
        "Browser streaming must not use Axios responseType stream; use fetch ReadableStream or EventSource in src/frontend/src/api",
      );
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);
  return violations;
}

function scanVue(filename, source, allowHttp) {
  const parsed = parseVueSfc(source, { filename });
  const violations = parsed.errors.map((error) => ({
    path: filename,
    line: error.loc?.start?.line ?? 1,
    message: `cannot parse Vue SFC: ${error.message ?? String(error)}`,
  }));
  for (const block of [parsed.descriptor.script, parsed.descriptor.scriptSetup]) {
    if (!block) continue;
    const lineOffset = source.slice(0, block.loc.start.offset).split("\n").length - 1;
    violations.push(...scanScript({ filename, source: block.content, lang: block.lang, lineOffset, allowHttp }));
  }
  return violations;
}

function displayPath(filename) {
  const relative = path.relative(PROJECT_ROOT, filename);
  return relative.startsWith("..") || path.isAbsolute(relative) ? filename : relative;
}

function main() {
  const { frontendSrc, apiRoot } = parseArgs(process.argv.slice(2));
  const violations = [];
  for (const filename of iterSourceFiles(frontendSrc)) {
    const source = fs.readFileSync(filename, "utf8");
    const allowHttp = isUnder(filename, apiRoot);
    if (path.extname(filename) === ".vue") violations.push(...scanVue(filename, source, allowHttp));
    else violations.push(...scanScript({ filename, source, allowHttp }));
  }
  for (const violation of violations.sort((left, right) => left.path.localeCompare(right.path) || left.line - right.line)) {
    process.stderr.write(`${displayPath(violation.path)}:${violation.line}: ${violation.message}\n`);
  }
  return violations.length === 0 ? 0 : 1;
}

try {
  process.exitCode = main();
} catch (error) {
  process.stderr.write(`frontend boundary failed: ${error.message ?? String(error)}\n`);
  process.exitCode = 1;
}
