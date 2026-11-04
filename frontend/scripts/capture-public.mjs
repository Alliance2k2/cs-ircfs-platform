// Capture only the isolated synthetic server: run_e2e_server.py --port 8772.
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const base = "http://127.0.0.1:8772";
const output = fileURLToPath(
  new URL("../../docs/images/public-refinement/", import.meta.url),
);
await mkdir(output, { recursive: true });
const browser = await chromium.launch(
  process.env.CI ? {} : { channel: "chrome" },
);
const layouts = [];
try {
  for (const width of [360, 390, 768, 1024, 1440]) {
    const context = await browser.newContext({
      viewport: { width, height: 960 },
      deviceScaleFactor: 1,
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    page.setDefaultNavigationTimeout(120_000);
    page.setDefaultTimeout(60_000);
    await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (route) => route.abort());
    await page.goto(base);
    await page.waitForFunction(
      () =>
        document.querySelector("#activity-badge")?.textContent ===
        "Demonstration data",
    );
    await page.evaluate(() => document.fonts.ready);
    for (const section of await page.locator("main section").all())
      await section.scrollIntoViewIfNeeded();
    await page.waitForFunction(() =>
      [...document.images].every(
        (image) => image.complete && image.naturalWidth > 0,
      ),
    );
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `${output}width-${width}.jpg`,
      fullPage: true,
      type: "jpeg",
      quality: 85,
    });
    if (width === 390) {
      await page.getByRole("button", { name: "Switch to Kinyarwanda" }).click();
      await page.screenshot({
        path: `${output}kinyarwanda-390.jpg`,
        fullPage: true,
        type: "jpeg",
        quality: 85,
      });
    }
    layouts.push({
      width,
      scrollWidth: await page.evaluate(
        () => document.documentElement.scrollWidth,
      ),
      brokenImages: await page
        .locator("img")
        .evaluateAll(
          (images) => images.filter((image) => !image.naturalWidth).length,
        ),
    });
    await context.close();
  }
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 150,
    downloadThroughput: 200000,
    uploadThroughput: 93750,
  });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await page.addInitScript(() => {
    window.__publicVitals = { lcp_ms: null, cls: 0 };
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries())
        window.__publicVitals.lcp_ms = entry.startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries())
        if (!entry.hadRecentInput) window.__publicVitals.cls += entry.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  await page.goto(base);
  await page.waitForFunction(
    () =>
      document.querySelector("#activity-badge")?.textContent ===
      "Demonstration data",
  );
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1500);
  const metrics = await page.evaluate(() => ({
    ...window.__publicVitals,
    paint: performance
      .getEntriesByType("paint")
      .map((entry) => ({ name: entry.name, milliseconds: entry.startTime })),
    initial_resource_bytes: performance
      .getEntriesByType("resource")
      .reduce((total, entry) => total + entry.transferSize, 0),
    resources: performance.getEntriesByType("resource").length,
    external_resources: performance
      .getEntriesByType("resource")
      .filter((entry) => new URL(entry.name).origin !== location.origin).length,
  }));
  await context.close();
  const report = {
    captured: new Date().toISOString(),
    source: "isolated synthetic preview",
    layouts,
    mobile_lab: {
      conditions:
        "390px, cold cache, 1.6Mbps down, 150ms latency, 4x CPU slowdown; one lab navigation, not real-user Core Web Vitals",
      ...metrics,
    },
  };
  await writeFile(
    `${output}verification.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
