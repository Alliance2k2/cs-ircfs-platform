import { asRole, expect } from "./fixtures";

const test = asRole("planner");

// Workflow 10: finding pages and reading the reports: search palette, language switch,
// monthly report by month, trends as a table, nutrition privacy and the map without a token.
test("search, language, monthly report, trends, nutrition and map", async ({ page }) => {
  await page.goto("/app/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible(); // the shell is ready for shortcuts
  await page.keyboard.press("Control+k");
  await page.getByRole("alertdialog", { name: "Search pages" }).getByRole("combobox").fill("trend");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/app\/trends$/);
  await expect(page.getByRole("navigation", { name: "Breadcrumb" })).toContainText("ReportsTrends");

  await page.getByRole("button", { name: "Show as table" }).click();
  await expect(page.getByRole("table", { name: "Twelve-month trends" }).getByRole("row")).toHaveCount(13);

  await page.goto("/app/monthly-report?month=2026-09");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("September 2026");
  await page.getByLabel("Month").fill("2026-08");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("August 2026");
  await expect(page).toHaveURL(/month=2026-08/);

  await page.goto("/app/nutrition");
  await expect(page.getByText("Fewer than 5 households: figures hidden to protect privacy", { exact: false })).toBeVisible();

  await page.goto("/app/map");
  await expect(page.getByText("MAPBOX_ACCESS_TOKEN", { exact: false })).toBeVisible();
  const layer = page.getByRole("checkbox", { name: /Pest heatmap/ });
  await layer.check();
  await expect(layer).toBeChecked();

  await page.getByRole("group", { name: /Language|Ururimi/ }).getByRole("button", { name: "RW" }).click();
  await expect(page.getByRole("button", { name: "RW" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("group", { name: /Language|Ururimi/ }).getByRole("button", { name: "EN" }).click();
});
