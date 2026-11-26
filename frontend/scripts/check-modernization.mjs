// Read-only local UI, accessibility, links and shared-device cache checks.
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const base = "http://127.0.0.1:8794";
const output = fileURLToPath(new URL("../../docs/images/modernization-20261124/after/", import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
const report = { source: "isolated synthetic preview; external requests blocked", pages: [], links: [], cache: null };
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  await context.route(/^https?:\/\/(?!127\.0\.0\.1:8794)/, route => route.abort());
  const page = await context.newPage();
  for (const path of ["/", "/login.html", "/register.html"]) {
    await page.goto(base + path);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    report.pages.push({ path, theme: "light", violations: result.violations.map(({ id, impact, nodes }) => ({ id, impact, nodes: nodes.map(({ target, failureSummary }) => ({ target, failureSummary })) })) });
    if (path === "/") {
      const links = await page.locator("a[href]").evaluateAll(nodes => [...new Set(nodes.map(node => node.getAttribute("href")))].filter(Boolean));
      for (const href of links) {
        const url = new URL(href, base);
        if (url.origin !== base) continue;
        if (url.hash && url.pathname === "/") {
          report.links.push({ href, found: await page.locator(`[id=${JSON.stringify(decodeURIComponent(url.hash.slice(1)))}]`).count() > 0 });
        } else {
          const response = await context.request.get(url.href);
          report.links.push({ href, status: response.status() });
        }
      }
    }
  }
  const login = await context.request.post(`${base}/api/v1/auth/login`, { data: { email: "admin@e2e.test", password: "e2e-password-2026" } });
  if (login.status() !== 200) throw new Error("Synthetic login failed");
  const api = await context.request.get(`${base}/api/v1/analytics/executive-overview`);
  report.cache = { status: api.status(), cacheControl: api.headers()["cache-control"] };
  for (const theme of ["light", "dark"]) {
    for (const path of ["/app/", "/app/map", "/app/assistant", "/app/climate", "/app/actions", "/app/management"]) {
      await page.evaluate(value => localStorage.setItem("cs-ircfs-theme-v2", value), theme);
      await page.goto(base + path, { waitUntil: "networkidle" });
      await page.locator("h1").first().waitFor();
      await page.waitForTimeout(500);
      const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      report.pages.push({ path, theme, violations: result.violations.map(({ id, impact, nodes }) => ({ id, impact, nodes: nodes.map(({ target, failureSummary }) => ({ target, failureSummary })) })) });
      if (theme === "dark") await page.screenshot({ path: `${output}${path.replaceAll("/", "-")}-dark.jpg`, fullPage: true, type: "jpeg", quality: 65 });
    }
  }
  await page.goto(`${base}/app/assistant`);
  await page.evaluate(() => localStorage.setItem("cs_ircfs_lang", "rw"));
  await page.reload();
  await page.getByRole("heading", { name: "Reka tubisuzume hamwe." }).waitFor();
  await page.setViewportSize({ width: 360, height: 1000 });
  await page.screenshot({ path: `${output}assistant-rw-360.jpg`, fullPage: true, type: "jpeg", quality: 70 });
  report.language = "RW welcome rendered using the existing language preference";
  await context.close();
} finally { await browser.close(); }
await writeFile(`${output}quality.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ pages: report.pages.length, violations: report.pages.filter(page => page.violations.length).map(page => ({ path: page.path, theme: page.theme, rules: page.violations.map(rule => rule.id) })), brokenLinks: report.links.filter(link => link.found === false || link.status >= 400), cache: report.cache }, null, 2));
