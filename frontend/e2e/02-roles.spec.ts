import { asRole, expect } from "./fixtures";

// Workflow 2: each role sees only what the backend lets it use.
const monitor = asRole("monitor");

monitor("a Citizen Science Monitor gets analytics but no staff tools or personal data", async ({ page }) => {
  await page.goto("/app/");
  const menu = page.getByRole("navigation", { name: "Menu" });
  await expect(menu.getByRole("link", { name: "Field reports" })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Priority actions" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Grievances" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Administration" })).toHaveCount(0);

  await page.goto("/app/admin");
  await expect(page.getByRole("alert")).toHaveText("This page is for administrators.");

  await page.goto("/app/field-reports");
  await expect(page.getByText("Phone numbers are masked and notes hidden for your role.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Export CSV" })).toHaveCount(0);
  await expect(page.getByRole("table")).not.toContainText("+2507885500");
});

const leader = asRole("leader");

leader("a cooperative leader starts on field reports, not on a refused overview", async ({ page }) => {
  await page.goto("/app/");
  await expect(page).toHaveURL(/\/app\/field-reports$/);
  const menu = page.getByRole("navigation", { name: "Menu" });
  await expect(menu.getByRole("link", { name: "Executive overview" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Crops & pests" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Irrigation command centre" })).toBeVisible();
});
