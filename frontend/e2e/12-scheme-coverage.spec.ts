import { asRole, expect } from "./fixtures";

const test = asRole("admin");

test("scheme coverage saves multiple sectors and remains editable on mobile", async ({ page }) => {
  await page.goto("/app/admin");
  await page.getByRole("tab", { name: "Scheme baselines" }).click();
  const row = page.getByRole("table").first().getByRole("row").filter({ hasText: "APEFA" }).first();
  await row.click();
  const drawer = page.getByRole("dialog");
  const coverage = drawer.getByRole("group", { name: "Scheme coverage sectors" });
  const boxes = coverage.getByRole("checkbox");
  await expect(boxes.nth(1)).toBeVisible();
  for (const box of await boxes.all()) await box.uncheck();
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  const saved = page.waitForResponse((response) => response.url().includes("/api/v1/irrigation-schemes/") && response.request().method() === "PATCH");
  await drawer.getByRole("button", { name: "Save", exact: true }).click();
  expect((await (await saved).json()).coverage_sector_ids).toHaveLength(2);
  await expect(drawer).not.toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: /Open Scheme baselines/ }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await page.locator("button button").count()).toBe(0);
});
