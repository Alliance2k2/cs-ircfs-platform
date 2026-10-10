import { asRole, expect } from "./fixtures";

const test = asRole("monitor");

// Workflow 7: the phone simulator registers a caller, records a rain reading and answers an SMS,
// and none of it is counted as field evidence.
test("USSD and SMS in the simulator are recorded as test data only", async ({ page }) => {
  await page.goto("/app/simulator");
  await page.getByLabel("Caller phone number").fill("+250788777001");
  const screen = page.locator('[aria-live="polite"]').filter({ hasText: /./ }).first();

  await page.getByRole("button", { name: "Dial *801#" }).click();
  await expect(screen).toContainText("Choose the sector where you live");
  await page.getByLabel("Your answer").fill("1");
  await page.getByRole("button", { name: "Send", exact: true }).first().click();
  await expect(screen).toContainText("choose your cell");
  await page.getByLabel("Your answer").fill("1");
  await page.getByRole("button", { name: "Send", exact: true }).first().click();
  await expect(screen).toContainText("Your location is saved");

  await page.getByRole("button", { name: "New session" }).click();
  await expect(screen).toContainText("1.");
  await page.getByLabel("Your answer").fill("3");
  await page.getByRole("button", { name: "Send", exact: true }).first().click();
  await expect(screen).toContainText("rainfall");
  await page.getByLabel("Your answer").fill("37.5");
  await page.getByRole("button", { name: "Send", exact: true }).first().click();
  await expect(screen).toContainText("37.5 mm");
  await expect(page.getByText("Recorded: irrigation report (simulator)")).toBeVisible();

  await page.getByLabel("Message").fill("IMVURA 4");
  await page.getByRole("button", { name: "Send", exact: true }).last().click();
  await expect(page.getByRole("listitem").filter({ hasText: /4 mm|Murakoze/ }).first()).toBeVisible();

  // Operations show the tests, marked as such; field reports never include them.
  await page.goto("/app/channels");
  await expect(page.getByRole("table").getByText("Simulator").first()).toBeVisible();
  await page.goto("/app/field-reports");
  await page.getByLabel("Type").selectOption("rain");
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("table")).not.toContainText("37.5 mm");
});
