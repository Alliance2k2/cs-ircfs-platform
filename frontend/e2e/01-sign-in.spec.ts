import { expect, test } from "@playwright/test";
import { PASSWORD, ROLES, storageFor } from "./fixtures";

test("public dashboard button requires sign-in even with stale cached account details", async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("cs_ircfs_account", JSON.stringify({ email: "expired@example.test", role: "administrator" }));
  });
  await page.goto("/");
  await page.getByRole("link", { name: "Open dashboard", exact: true }).click();
  await expect(page).toHaveURL(/\/login\.html\?next=%2Fapp%2F$/);
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.locator("#signed-in")).toBeHidden();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("cs_ircfs_account"))).toBeNull();
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
  await page.goto("/app/");
  await expect(page).toHaveURL(/\/login\.html/);
});

test.describe("existing server session", () => {
  test.use({ storageState: storageFor("planner") });

  test("sign-in page identifies the account from its session cookie", async ({ page }) => {
    await page.goto("/login.html");
    await expect(page.locator("#signed-in")).toBeVisible();
    await expect(page.locator("#signed-in")).toContainText(ROLES.planner);
    await page.getByRole("link", { name: "Continue to the dashboard" }).click();
    await expect(page).toHaveURL(/\/app\/$/);
    await expect(page.getByRole("button", { name: "Account menu" })).toContainText("E2E Planner");
  });
});

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
