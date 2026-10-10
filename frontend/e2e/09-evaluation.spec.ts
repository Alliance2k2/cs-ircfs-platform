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
  await expect(padab).toContainText("Harvested area recorded on each harvest report");

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.csv$/);
  await expect(page.getByRole("button", { name: "Print" })).toBeEnabled();
});
