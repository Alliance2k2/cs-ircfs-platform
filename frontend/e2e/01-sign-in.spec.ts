import { expect, test } from "@playwright/test";
import { PASSWORD, ROLES } from "./fixtures";

// Workflow 1: a planner signs in, lands on the page they asked for, and signs out.
test("sign in returns to the requested page and sign out ends the session", async ({ page }) => {
  await page.goto("/app/field-reports");
  await expect(page).toHaveURL(/\/login\.html\?next=%2Fapp%2Ffield-reports/);

  await page.getByLabel("Email address").fill(ROLES.planner);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/app\/field-reports$/);
  await expect(page.getByRole("heading", { level: 1, name: "Field reports" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Account menu" })).toContainText("E2E Planner");

  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\.html/);

  await page.goto("/app/");
  await expect(page).toHaveURL(/\/login\.html/);
});

test("a wrong password is refused with a clear message", async ({ page }) => {
  await page.goto("/login.html");
  await page.getByLabel("Email address").fill(ROLES.planner);
  await page.getByLabel("Password", { exact: true }).fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Incorrect email or password.")).toBeVisible();
  await expect(page).toHaveURL(/\/login\.html/);
});
