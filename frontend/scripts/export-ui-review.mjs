// Candidate hardcoded UI copy for native review; never marks wording approved.
import ts from "typescript";
import { readdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { join, relative } from "node:path";
const root = fileURLToPath(new URL("../src/", import.meta.url));
const entries = [];
const labels = new Set(["aria-label", "title", "placeholder", "label", "caption", "description", "note", "emptyMessage", "header"]);
async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) { await walk(path); continue; }
    if (!entry.name.endsWith(".tsx") || entry.name.includes(".test.")) continue;
    const source = ts.createSourceFile(path, await readFile(path, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const record = (node, text) => {
      const english = text.replace(/\s+/g, " ").trim();
      if (!/[A-Za-z]/.test(english)) return;
      entries.push({ file: relative(root, path).replaceAll("\\", "/"), line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1, english, kinyarwanda: "", approved: false });
    };
    const visit = node => {
      if (ts.isJsxText(node)) record(node, node.text);
      if (ts.isJsxAttribute(node) && labels.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) record(node, node.initializer.text);
      if (ts.isPropertyAssignment(node) && labels.has(node.name.getText(source)) && ts.isStringLiteral(node.initializer)) record(node, node.initializer.text);
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
}
await walk(root);
const report = { review_status: "pending_native_review", reviewer: "", evidence_reference: "", note: "Source-located candidates beyond the keyed translation pack. Some are brand names; review in context. Does not claim complete extraction of dynamic strings or authorize automatic replacement.", entries };
await writeFile(new URL("../../docs/modernization-ui-review-20261124.json", import.meta.url), JSON.stringify(report, null, 2) + "\n");
console.log(`${entries.length} source-located UI candidates exported; no translations approved.`);
