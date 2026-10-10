import { asRole, expect, expectToast } from "./fixtures";

const test = asRole("officer");

// Workflow 5: a grievance is triaged, assigned, resolved and answered, and stays anonymous.
test("work a grievance through to closing the loop without revealing the sender", async ({ page }) => {
  await page.goto("/app/grievances");
  await expect(page.getByText("No phone number or name is stored with a grievance.", { exact: false })).toBeVisible();
  await page.getByRole("table").getByRole("button", { name: /Water Pricing/ }).first().click();

  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("Grievance");
  await expect(drawer).not.toContainText("+2507");

  await drawer.getByLabel("Status").selectOption("in_progress");
  await drawer.getByLabel("Assigned to").selectOption({ index: 1 });
  await drawer.getByRole("button", { name: "Save" }).click();
  await expectToast(page, "Saved.");

  await drawer.getByLabel("Status").selectOption("resolved");
  await drawer.getByLabel(/Action taken/).fill("Water fee instalments agreed with the cooperative for this season.");
  await drawer.getByRole("button", { name: "Save" }).click();
  await expectToast(page, "Saved.");

  await drawer.getByRole("button", { name: "Tell the community by SMS" }).click();
  const confirm = page.getByRole("alertdialog");
  await expect(confirm).toContainText("people in the cell would receive:");
  await expect(confirm).toContainText("FB-");
  await confirm.getByRole("button", { name: "Cancel" }).click();
  await expect(confirm).toHaveCount(0);
  await expect(drawer).toBeVisible();
});
