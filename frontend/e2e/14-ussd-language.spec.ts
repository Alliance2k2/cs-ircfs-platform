import { randomInt } from "node:crypto";
import { asRole, expect } from "./fixtures";

const test = asRole("monitor");

for (const language of ["rw", "en"] as const) {
  test(`field USSD selects, persists and changes ${language} without the English aid`, async ({ page }) => {
    await page.goto("/app/simulator");
    const phone = `+25079${randomInt(1_000_000, 10_000_000)}`;
    await page.getByLabel("Caller phone number").fill(phone);
    await page.getByRole("checkbox").uncheck();
    const screen = page.locator('[aria-live="polite"]').first();
    const answer = async (value: string) => {
      await page.getByLabel("Your answer").fill(value);
      await page.getByRole("button", { name: "Send", exact: true }).first().click();
    };
    await page.getByRole("button", { name: "Dial *801#" }).click();
    await expect(screen).toContainText("1. Ikinyarwanda");
    await expect(screen).toContainText("2. English");
    await answer(language === "rw" ? "1" : "2");
    await expect(screen).toContainText(language === "rw" ? "Hitamo umurenge" : "Choose the sector");
    await answer("1");
    await expect(screen).toContainText(language === "rw" ? "hitamo akagari" : "choose your cell");
    await answer("1");
    await expect(screen).toContainText(language === "rw" ? "Aho utuye habitswe" : "Your location is saved");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(screen).toContainText(language === "rw" ? "Kaze kuri" : "Welcome to");
    await expect(screen).toContainText(language === "rw" ? "6. Imirire" : "6. Household nutrition");
    await answer("3");
    await expect(screen).toContainText(language === "rw" ? "Andika imvura" : "Enter today's rainfall");
    await answer("7.25");
    await expect(screen).toContainText(language === "rw" ? "yanditswe" : "recorded");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(screen).toContainText("0.");
    await answer("0");
    await expect(screen).toContainText("Choose language");
    await answer(language === "rw" ? "2" : "1");
    await expect(screen).toContainText(language === "rw" ? "Welcome to" : "Kaze kuri");
    await expect(screen).not.toContainText("Choose the sector");
    await expect(screen).not.toContainText("Hitamo umurenge");
    await page.getByRole("button", { name: "Hang up", exact: true }).click();
    await page.reload();
    // Keep the same caller after reload: the preference lives on the server profile.
    await page.getByLabel("Caller phone number").fill(phone);
    await page.getByRole("checkbox").uncheck();
    await page.getByRole("button", { name: "Dial *801#" }).click();
    await expect(screen).toContainText(language === "rw" ? "Welcome to" : "Kaze kuri");
    await answer("0");
    await expect(screen).toContainText("Choose language");
    await answer("9");
    await expect(screen).toContainText("That answer is not valid");
    await page.getByRole("button", { name: "New session" }).click();
    await expect(screen).toContainText(language === "rw" ? "Welcome to" : "Kaze kuri");
  });
}
