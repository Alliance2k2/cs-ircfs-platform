import { expect, test } from "@playwright/test";
import { expectToast, storageFor } from "./fixtures";

// Workflow 8: a new person registers, cannot sign in until approved, and an administrator
// approves them and changes their role, which the audit log records.
test("register, approve, change role and audit", async ({ browser, page }) => {
  const email = `new.officer.${Date.now()}@e2e.test`;
  const password = "Registered-pass-2026";

  await page.goto("/register.html");
  await page.getByLabel("First name").fill("Nadia");
  await page.getByLabel("Surname").fill("Uwase");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("A district administrator will approve it", { exact: false })).toBeVisible();

  const refused = await page.request.post("/api/v1/auth/login", { data: { email, password } });
  expect(refused.status()).toBe(403);
  expect(await refused.text()).toContain("waiting for approval");

  const admin = await browser.newContext({ storageState: storageFor("admin") });
  const adminPage = await admin.newPage();
  await adminPage.goto("/app/admin");
  await expect(adminPage.getByText("accounts are waiting for approval", { exact: false })).toBeVisible();
  const row = adminPage.getByRole("row", { name: new RegExp(email.replace(/\./g, "\\.")) });
  await row.getByRole("button", { name: "Approve" }).click();
  const confirm = adminPage.getByRole("alertdialog");
  await expect(confirm).toContainText("Approve Nadia Uwase as Citizen science monitor?");
  await confirm.getByRole("button", { name: "Confirm" }).click();
  await expectToast(adminPage, "Account active.");

  await row.getByRole("combobox", { name: "Role for Nadia Uwase" }).selectOption("district_officer");
  await adminPage.getByRole("alertdialog").getByRole("button", { name: "Confirm" }).click();
  await expectToast(adminPage, "Role updated.");

  const accepted = await page.request.post("/api/v1/auth/login", { data: { email, password } });
  expect(accepted.ok()).toBe(true);
  expect((await accepted.json()).access_token).toBeTruthy();

  await adminPage.getByRole("tab", { name: "Audit log" }).click();
  await expect(adminPage.getByRole("table")).toContainText("account.update");
  await expect(adminPage.getByRole("table")).toContainText(email);
  await admin.close();
});
