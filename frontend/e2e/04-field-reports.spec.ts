import { asRole, expect, expectToast } from "./fixtures";

const test = asRole("planner");

// Workflow 4: a planner checks a pest report, cannot reject without a reason, and verifies it.
test("verify a field report and find it among verified reports", async ({ page }) => {
  await page.goto("/app/field-reports");
  await page.getByLabel("Type").selectOption("pest");
  const table = page.getByRole("table");
  const first = table.getByRole("row").nth(1);
  const title = (await first.getByRole("button").first().innerText()).split("\n")[0]!;
  await first.getByRole("button").first().click();

  const drawer = page.getByRole("dialog");
  await expect(drawer.getByText("Unverified").first()).toBeVisible();
  await drawer.getByRole("button", { name: "Reject" }).click();
  await expect(drawer.getByLabel("Verification note")).toHaveAttribute("aria-invalid", "true");

  await drawer.getByLabel("Verification note").fill("Checked on the farm with the cooperative leader.");
  await drawer.getByRole("button", { name: "Mark verified" }).click();
  await expectToast(page, "Report marked verified.");
  await expect(drawer.getByRole("button", { name: "Mark unverified" })).toBeVisible();
  await expect(drawer).toContainText("Checked on the farm with the cooperative leader.");
  await drawer.getByRole("button", { name: "Close" }).click();

  await page.getByLabel("Verification").selectOption("verified");
  await expect(page.getByRole("table")).toContainText(title);
});

test("export the filtered reports as CSV without phone numbers", async ({ page }) => {
  await page.goto("/app/field-reports");
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  const file = await download;
  const text = await (await file.createReadStream()).toArray().then((chunks) => Buffer.concat(chunks).toString("utf8"));
  expect(text.split("\n")[0]).toContain("id,source,kind,title");
  expect(text).not.toContain("+2507");
});
