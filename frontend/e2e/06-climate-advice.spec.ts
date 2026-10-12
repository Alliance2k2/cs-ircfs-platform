import { asRole, expect, expectToast } from "./fixtures";

// Workflow 6: weekly irrigation advice is previewed before it is sent (dry-run SMS here).
const planner = asRole("planner");

planner("preview, cancel, then send the week's advice", async ({ page }) => {
  await page.goto("/app/climate");
  await expect(page.getByRole("table", { name: "Climate & irrigation advice" })).toContainText("Dry: irrigate more");
  await expect(page.getByText("Gauges are citizen instruments", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: "Send advice by SMS" }).click();
  const confirm = page.getByRole("alertdialog");
  await expect(confirm).toContainText("24 people in 3 sectors would receive this week's advice.");
  await confirm.getByRole("button", { name: "Cancel" }).click();
  await expect(confirm).toHaveCount(0);

  await page.getByRole("button", { name: "Send advice by SMS" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Send" }).click();
  await expectToast(page, "Advice recorded for 24 people.");
});

const officer = asRole("officer");

officer("officers read the advice but cannot send it", async ({ page }) => {
  await page.goto("/app/climate");
  await expect(page.getByRole("table", { name: "Climate & irrigation advice" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send advice by SMS" })).toHaveCount(0);
});
