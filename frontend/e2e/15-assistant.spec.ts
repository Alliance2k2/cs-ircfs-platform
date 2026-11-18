import { asRole, expect } from "./fixtures";

const test = asRole("planner");
test("staff document assistant retrieves sources, refuses missing evidence and clears the conversation", async ({ page }) => {
  await page.goto("/app/assistant");
  await expect(page.getByRole("heading", { level: 1, name: "Document assistant" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Manage knowledge sources" })).toHaveCount(0);
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

test("follow-up context and language choice keep source evidence visible", async ({ page }) => {
  await page.goto("/app/assistant");
  await page.getByLabel("Your question").fill("How do I change the USSD language?");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  const conversation = page.getByRole("list", { name: "Conversation" });
  await expect(conversation).toContainText("option 0");
  await page.getByLabel("Question language").selectOption("rw");
  await page.getByLabel("Your question").fill("What about returning callers?");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  await expect(conversation).toContainText("pending native review");
  await expect(conversation.getByRole("listitem")).toHaveCount(2);
  await page.getByLabel("Your question").fill("Nigute nahindura ururimi kuri USSD?");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  await expect(conversation.getByRole("listitem")).toHaveCount(3);
  await expect(conversation.getByRole("listitem").last()).toContainText("pending native review");
  await conversation.getByRole("button", { name: "Helpful", exact: true }).last().click();
  await expect(conversation).toContainText("Feedback recorded without your question or answer");
});

const adminTest = asRole("admin");
adminTest("administrator can inspect knowledge management without enabling uploads", async ({ page }) => {
  await page.goto("/app/assistant");
  await expect(page.getByRole("heading", { name: "Manage knowledge sources" })).toBeVisible();
  await page.getByRole("button", { name: "Load knowledge sources" }).click();
  await expect(page.getByLabel("Source title")).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload and index for review" })).toBeDisabled();
});

adminTest("synthetic source stays pending until review and disappears after removal", async ({ page }) => {
  await page.goto("/app/assistant");
  await page.getByLabel("Source title", { exact: true }).fill("Synthetic browser pump procedure");
  await page.getByLabel("Document file").setInputFiles({ name: "synthetic-pump.txt", mimeType: "text/plain", buffer: Buffer.from("Synthetic inspection procedure: record the heliostat isolation checklist. This is test material, not agricultural advice.") });
  await page.getByRole("button", { name: "Upload and index for review" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("approval is required");
  await page.getByRole("button", { name: "Upload and index for review" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("This content already exists with status: pending");
  await page.getByLabel("Your question").fill("heliostat isolation checklist");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  const conversation = page.getByRole("list", { name: "Conversation" });
  await expect(conversation.getByRole("listitem").last()).not.toContainText("Synthetic inspection procedure");
  await page.getByRole("button", { name: "Review Synthetic browser pump procedure revision 1" }).click();
  await page.getByText("Page/section 1", { exact: true }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("Synthetic inspection procedure");
  await page.getByLabel("Review/approval reference").fill("Synthetic E2E review only");
  await page.getByRole("button", { name: "Approve reviewed version" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("approved for authorized retrieval");
  await page.getByLabel("Your question").fill("heliostat isolation checklist");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  await expect(conversation.getByRole("listitem").last()).toContainText("Synthetic inspection procedure");
  await page.getByRole("button", { name: "Remove Synthetic browser pump procedure from retrieval" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("chunks and vectors deleted");
  await page.getByLabel("Your question").fill("heliostat isolation checklist");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  await expect(conversation.getByRole("listitem").last()).not.toContainText("Synthetic inspection procedure");
});
