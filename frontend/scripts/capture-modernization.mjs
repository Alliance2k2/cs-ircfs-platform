// Only synthetic accounts/data on the dedicated modernization preview are captured.
import { chromium } from "@playwright/test";
import { mkdir, readdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const phase = process.argv[2] ?? "before";
if (!["before", "after"].includes(phase)) throw new Error("Use before or after");
const base = "http://127.0.0.1:8794";
const output = fileURLToPath(new URL(`../../docs/images/modernization-20261124/${phase}/`, import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
const results = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const auth = await context.request.post(`${base}/api/v1/auth/login`, { data: { email: "admin@e2e.test", password: "e2e-password-2026" } });
  if (auth.status() !== 200) throw new Error("Expected isolated synthetic account");
  await context.route(/^https?:\/\/(?!127\.0\.0\.1:8794)/, route => route.abort());
  const page = await context.newPage();
  let pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  page.setDefaultNavigationTimeout(60_000);
  const classic = (await readdir(new URL("../../dashboard/", import.meta.url))).filter(name => name.endsWith(".html"));
  const workspaces = ["", "actions", "field-reports", "crops", "nutrition", "irrigation", "climate", "map", "evaluation", "grievances", "cooperatives", "channels", "simulator", "trends", "monthly-report", "management", "admin", "assistant"];
  const paths = ["/", ...classic.filter(name => name !== "index.html").map(name => `/${name}`), ...workspaces.map(name => `/app/${name}`)];
  for (const path of paths) {
    try {
      pageErrors = [];
      const response = await page.goto(base + path, { waitUntil: "domcontentloaded" });
      await page.locator("h1").first().waitFor({ timeout: 20_000 });
      await page.waitForTimeout(400);
      const name = path === "/" ? "public" : path.replace(/^\//, "").replaceAll("/", "-").replace(".html", "");
      await page.screenshot({ path: `${output}${name}.jpg`, fullPage: true, type: "jpeg", quality: 65 });
      results.push({ path, status: response.status(), title: await page.title(), heading: await page.locator("h1").first().innerText(), width: 1440, scrollWidth: await page.evaluate(() => document.documentElement.scrollWidth), pageErrors: [...pageErrors], alerts: await page.getByRole("alert").allTextContents(), mapSdkLoaded: await page.evaluate(() => performance.getEntriesByType("resource").some(entry => /SectorMap-.*\.js/.test(entry.name))) });
    } catch (error) { results.push({ path, error: error.message.slice(0, 200) }); }
  }
  for (const width of [360, 768]) {
    await page.setViewportSize({ width, height: 1000 });
    const narrowPaths = phase === "after" && width === 360 ? ["/", "/login.html", "/register.html", ...workspaces.map(name => `/app/${name}`)] : ["/", "/login.html", "/register.html", "/app/", "/app/map", "/app/assistant"];
    for (const path of narrowPaths) {
      try {
        pageErrors = [];
        await page.goto(base + path, { waitUntil: "domcontentloaded" });
        await page.locator("h1").first().waitFor({ timeout: 20_000 });
        await page.waitForTimeout(300);
        const name = path === "/" ? "public" : path.replace(/^\//, "").replaceAll("/", "-").replace(".html", "");
        await page.screenshot({ path: `${output}${name}-${width}.jpg`, fullPage: true, type: "jpeg", quality: 65 });
        results.push({ path, width, scrollWidth: await page.evaluate(() => document.documentElement.scrollWidth), pageErrors: [...pageErrors], alerts: await page.getByRole("alert").allTextContents() });
      } catch (error) { results.push({ path, width, error: error.message.slice(0, 150) }); }
    }
  }
  await context.close();
} finally { await browser.close(); }
await writeFile(`${output}audit.json`, JSON.stringify({ phase, source: "isolated synthetic preview; external services blocked", results }, null, 2));
console.log(JSON.stringify({ phase, pages: results.length, errors: results.filter(r => r.error), overflow: results.filter(r => r.scrollWidth > r.width) }, null, 2));
