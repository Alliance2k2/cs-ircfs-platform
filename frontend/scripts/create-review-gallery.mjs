import { readFile, writeFile } from "node:fs/promises";
const root = new URL("../../docs/images/modernization-20261124/", import.meta.url);
const audit = JSON.parse(await readFile(new URL("after/audit.json", root), "utf8"));
const escape = value => String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const cards = audit.results.filter(row => row.width === 1440).map(row => {
  const name = row.path === "/" ? "public" : row.path.replace(/^\//, "").replaceAll("/", "-").replace(".html", "");
  return `<figure><a href="after/${name}.jpg"><img src="after/${name}.jpg" alt="${escape(row.heading)}" loading="lazy"></a><figcaption><strong>${escape(row.path)}</strong><small>${escape(row.heading)}</small><p><a href="before/${name}.jpg">Before</a> &middot; <a href="after/${name}.jpg">After</a></p></figcaption></figure>`;
});
const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CS-IRCFS modernization review</title><style>body{margin:24px;background:#f8fafc;color:#17352c;font:14px Arial,sans-serif}h1{color:#064e3b}nav{margin:16px 0}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}figure{margin:0;min-width:0;border:1px solid #cddbd3;border-radius:12px;background:white;overflow:hidden}img{width:100%;height:180px;object-fit:cover;object-position:top}figcaption{padding:12px}a{color:#065f46}small{display:block;margin-top:6px}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style></head><body><h1>CS-IRCFS modernization review</h1><p>24 November 2026 &middot; isolated synthetic data. Click an image for the full page.</p><nav><a href="../../modernization-2026-11-24.md">Verification report</a> &middot; <a href="after/audit.json">Responsive capture manifest</a> &middot; <a href="after/quality.json">Accessibility and links</a></nav><div class="grid">${cards.join("")}</div></body></html>`;
await writeFile(new URL("index.html", root), page, "utf8");
console.log(`${cards.length} desktop comparisons linked; original capture files unchanged.`);
