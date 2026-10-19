#!/usr/bin/env node
// Diagram check for the pr-story skill: does Pele draw this Mermaid source as written?
//
//   check-diagram.mjs [FILE] [--svg PATH]   check FILE, or stdin when FILE is absent or -
//
// Exit 0 prints `ok: <type>` (sequence, state, flowchart, ...) and, with --svg, writes
// the SVG. Exit 1 means Pele rejects the source, or would silently drop a label's text;
// the reason goes to stderr. Exit 2 is a usage or file error, exit 3 a missing install.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SKILL_DIR = fileURLToPath(new URL("..", import.meta.url));
// Pele draws labels as SVG text: these tags survive, every other tag-like token is
// dropped, and with it text such as `<User>` in `Promise<User>`.
const KEPT_TAGS = new Set(["br", "b", "i", "em", "strong"]);

function fail(msg, code) {
  console.error(`check-diagram: ${msg}`);
  process.exit(code);
}

function parseArgs(argv) {
  const args = { file: "-", svg: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--svg") {
      if (!argv[i + 1]) fail("--svg needs a path", 2);
      args.svg = argv[++i];
    } else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("usage: check-diagram.mjs [FILE] [--svg PATH]");
      process.exit(0);
    } else if (argv[i].startsWith("--")) {
      fail(`unknown option ${argv[i]}`, 2);
    } else {
      args.file = argv[i];
    }
  }
  return args;
}

function readSource(file) {
  if (file === "-" && process.stdin.isTTY) fail("pass a FILE or pipe the source on stdin", 2);
  try {
    return readFileSync(file === "-" ? 0 : file, "utf8");
  } catch (e) {
    fail(`cannot read ${file === "-" ? "stdin" : file}: ${e.message}`, 2);
  }
}

// Tag-like tokens Pele would drop, as `line N: <tag>`. `%%` comments and `<<choice>>`
// style annotations are not labels.
function droppedTags(src) {
  const found = [];
  src.split("\n").forEach((line, i) => {
    if (line.trim().startsWith("%%")) return;
    for (const m of line.matchAll(/(?<!<)<(\/?)([A-Za-z][\w-]*)([^<>]*)>(?!>)/g)) {
      const bare = /^\s*\/?\s*$/.test(m[3]);
      if (!(KEPT_TAGS.has(m[2].toLowerCase()) && bare)) found.push(`line ${i + 1}: ${m[0]}`);
    }
  });
  return found;
}

async function loadPele() {
  try {
    return await import("pele");
  } catch (e) {
    if (e.code !== "ERR_MODULE_NOT_FOUND") throw e;
    fail(`pele is not installed; run: npm ci --prefix "${SKILL_DIR}" --ignore-scripts --no-audit --no-fund`, 3);
  }
}

const args = parseArgs(process.argv.slice(2));
const src = readSource(args.file);
const { render, supports, detectType, PeleError } = await loadPele();

if (!src.trim()) fail("the source is empty", 1);
if (!supports(src)) {
  const first = src.trim().split("\n")[0];
  fail(
    `unsupported diagram: Pele detects no diagram type in the first line \`${first.slice(0, 60)}\`. ` +
      "Start with a keyword such as sequenceDiagram, stateDiagram-v2 or flowchart TD, without the ``` fence.",
    1,
  );
}

let result;
try {
  result = render(src);
} catch (e) {
  if (!(e instanceof PeleError)) throw e;
  const at = e.line ? ` at line ${e.line}, column ${e.column}` : "";
  fail(`${e.code} error in ${e.type ?? detectType(src) ?? "unknown"} diagram${at}\n${e.message}`, 1);
}

const dropped = droppedTags(src);
if (dropped.length) {
  fail(
    `Pele draws labels as plain SVG text and drops these tags, with their text:\n  ${dropped.join("\n  ")}\n` +
      "Reword without angle brackets; a line break is <br>.",
    1,
  );
}

if (args.svg) {
  try {
    writeFileSync(args.svg, result.svg);
  } catch (e) {
    fail(`cannot write ${args.svg}: ${e.message}`, 2);
  }
}
console.log(`ok: ${result.type}`);
