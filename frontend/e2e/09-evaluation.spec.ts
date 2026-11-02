import { asRole, expect, expectToast } from "./fixtures";

const test = asRole("admin");

// Workflow 9: an administrator records a scheme's yield target with its source document, and the
// evaluation lab shows it as documented without inventing an achievement figure.
test("record a scheme baseline and read the evaluation evidence", async ({ page }) => {
  await page.goto("/app/admin");
  await page.getByRole("tab", { name: "Scheme baselines" }).click();
  await page.getByRole("table").getByRole("button", { name: /PADAB/ }).first().click();

  const drawer = page.getByRole("dialog");
  await drawer.getByLabel("Yield target (tons)").fill("150");
  await drawer.getByLabel("Source document").fill("");
  await drawer.getByRole("button", { name: "Save" }).click();
  await expect(drawer.getByLabel("Source document")).toHaveAttribute("aria-invalid", "true");

  await drawer.getByLabel("Source document").fill("PADAB feasibility study, AfDB, 2014, table 4.2 (E2E)");
  await drawer.getByRole("button", { name: "Save" }).click();
  await expectToast(page, "Scheme baseline saved.");

  await page.goto("/app/evaluation");
  const padab = page.locator("section").filter({ has: page.getByRole("heading", { level: 2, name: /^PADAB/ }) }).first();
  await expect(padab).toContainText("Documented");
  await expect(padab).toContainText("table 4.2 (E2E)");
  await expect(padab).toContainText("Not computable yet");
  await expect(padab).toContainText("Verified measured harvests with harvested area and matching crop, season and year");

  // These explicit synthetic targets and measurements exist only in the disposable E2E database.
  await page.goto("/app/admin");
  await page.getByRole("tab", { name: "Scheme baselines" }).click();
  await page.getByLabel("Irrigation scheme", { exact: true }).selectOption({ label: "PADAB" });
  await page.getByLabel(/^Crop/).fill("Rice");
  await page.getByLabel("Agricultural season").fill("E2E-A");
  await page.getByLabel("Reference year").fill("2026");
  await page.getByLabel(/^Expected yield/).fill("4000");
  await page.getByLabel("Measurement unit").selectOption("kg/ha");
  await page.getByLabel(/^Official source/).fill("Synthetic E2E source (never pilot evidence)");
  await page.getByLabel(/^Source document reference/).fill("E2E fixture table 1");
  await page.getByRole("button", { name: "Save unapproved version" }).click();
  await expectToast(page, "Target version saved");
  await page.getByLabel("Date of approval").fill("2026-01-01");
  await page.getByRole("button", { name: "Approve official target" }).click();
  await expect(page.getByRole("button", { name: "Approve official target" })).toHaveCount(0);
  const schemes = await (await page.request.get("/api/v1/irrigation-schemes")).json();
  const scheme = schemes.find((s: { name: string }) => s.name === "PADAB");
  const created = await page.request.post("/api/v1/citizen-reports", { data: {
    scheme_id: scheme.id, crop_type: "Rice", season: "E2E-A", reference_year: 2026,
    observed_quantity: 6000, harvest_unit: "kg", cultivated_area_hectares: 3, harvested_area_hectares: 2,
    harvest_date: "2026-08-01", observation_type: "measured", data_source: "Synthetic E2E weighing fixture",
  } });
  expect(created.status()).toBe(201);
  const observation = await created.json();
  expect((await page.request.patch(`/api/v1/field-reports/crop/${observation.id}/verification`, { data: { status: "verified" } })).status()).toBe(200);
  await page.goto("/app/evaluation");
  await expect(page.getByText("75%", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/E2E-A \/ 2026/)).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.csv$/);
  await expect(page.getByRole("button", { name: "Print" })).toBeEnabled();
});
