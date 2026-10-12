import { asRole, expect, expectToast } from "./fixtures";

const test = asRole("officer");

// Workflow 3: an officer assigns and resolves an incident case, then closes the loop by SMS (dry-run).
test("assign, resolve and notify the community about a case", async ({ page }) => {
  await page.goto("/app/actions");
  const table = page.getByRole("table");
  await table.getByRole("button", { name: /PADAB Pumping Station 1 is offline/ }).first().click();

  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("Incident case");
  await expect(drawer.getByRole("button", { name: "Tell the community by SMS" })).toBeDisabled();

  await drawer.getByLabel("Status").selectOption("resolved");
  await drawer.getByRole("button", { name: "Save" }).click();
  await expect(drawer.getByText("Required to resolve or close.", { exact: false })).toBeVisible();
  await expect(drawer.getByLabel(/Action taken/)).toHaveAttribute("aria-invalid", "true");

  await drawer.getByLabel("Assigned to").selectOption({ label: "E2E Officer · Bugesera District" });
  await drawer.getByLabel("Deadline").fill("2026-12-31");
  await drawer.getByLabel(/Action taken/).fill("Pump motor rewound and restarted by the scheme technician.");
  await drawer.getByRole("button", { name: "Save" }).click();
  await expectToast(page, "Saved.");

  // The history is the audit trail, and the drawer stays open although the case left the open queue.
  await expect(drawer.getByRole("region", { name: "History" })).toContainText("Pump motor rewound");
  await drawer.getByRole("button", { name: "Tell the community by SMS" }).click();

  const confirm = page.getByRole("alertdialog");
  await expect(confirm).toContainText("2 people in the cell would receive:");
  await confirm.getByRole("button", { name: "Send" }).click();
  await expectToast(page, "Message recorded for 2 people.");
});
