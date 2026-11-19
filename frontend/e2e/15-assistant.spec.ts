import { asRole, expect } from "./fixtures";

const test = asRole("planner");
test("staff document assistant retrieves sources, refuses missing evidence and clears the conversation", async ({ page }) => {
  await page.goto("/app/assistant");
  await expect(page.getByRole("heading", { level: 1, name: "Document assistant" })).toBeVisible();
  await page.getByRole("button", { name: "How do I change the USSD language?" }).click();
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  const conversation = page.getByRole("list", { name: "Conversation" });
  await expect(conversation).toContainText("option 0");
  await expect(conversation).toContainText("no AI-generated answer");
  await conversation.locator("summary").filter({ hasText: "USSD language" }).click();
  await expect(conversation).toContainText("docs/engineering-validation-2026-11-13.md");
  await page.getByLabel("Your question").fill("quantum entanglement spectroscopy");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  await expect(conversation).toContainText("could not find supporting");
  await page.getByRole("button", { name: "Clear conversation" }).click();
  await expect(conversation.getByRole("listitem")).toHaveCount(0);
});
