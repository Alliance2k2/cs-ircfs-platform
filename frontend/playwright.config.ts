import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * Browser end-to-end tests against a real FastAPI server and the built app (npm run build first).
 * backend/scripts/run_e2e_server.py starts a throwaway SQLite platform with demonstration
 * data, one account per role and every external service (SMS, airtime, weather, Mapbox) off.
 *
 * PYTHON picks the interpreter: "python" in CI, e.g. ../.venv/Scripts/python on Windows.
 * Locally the installed Chrome is used; CI installs Playwright's Chromium.
 */
const PORT = 8770;
// A bare command name ("python" in CI) is looked up on PATH; a relative path such as
// ../.venv/Scripts/python is made absolute and quoted, as Windows cmd cannot run "../x".
const interpreter = process.env.PYTHON ?? "python";
const python = /[\\/]/.test(interpreter) ? `"${resolve(interpreter)}"` : interpreter;
const server = `"${resolve("../backend/scripts/run_e2e_server.py")}"`;

export default defineConfig({
  testDir: "./e2e",
  // Workflows change shared server state (cases, accounts), so they run one at a time.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "en-GB",
    timezoneId: "Africa/Kigali",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], ...(process.env.CI ? {} : { channel: "chrome" }) },
    },
  ],
  webServer: {
    command: `${python} ${server} --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
  },
});
