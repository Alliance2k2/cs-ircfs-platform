import { asRole, expect } from "./fixtures";

const test = asRole("admin");
test.skip(process.env.E2E_LOCAL_AI !== "true", "Explicit local CPU model test; no downloads or paid APIs in ordinary tests");

test("local model answers from an uploaded, reviewed and selected document", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/app/assistant");
  await expect(page.getByText("Local AI · On this laptop", { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/assistant-local-ai-welcome.png", fullPage: true });
  await page.getByRole("button", { name: "Attach or choose documents" }).click();
  await page.getByRole("button", { name: "Upload & review", exact: true }).click();
  await page.getByLabel("Source title", { exact: true }).fill("Synthetic heliostat checklist");
  await page.getByLabel("Document file").setInputFiles({ name: "synthetic-checklist.txt", mimeType: "text/plain", buffer: Buffer.from("The heliostat inspection begins with an isolation checklist. Record completion in the maintenance log.") });
  await page.getByRole("button", { name: "Upload and index for review" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("approval is required");
  await page.getByRole("button", { name: "Review Synthetic heliostat checklist revision 1" }).click();
  await page.getByLabel("Review/approval reference").fill("Synthetic test review only");
  await page.getByRole("button", { name: "Approve reviewed version" }).click();
  await expect(page.getByRole("region", { name: "Knowledge management" })).toContainText("approved for authorized retrieval");
  await page.getByRole("checkbox", { name: /Synthetic heliostat checklist/ }).check();
  await page.screenshot({ path: "test-results/assistant-document-library.png", fullPage: true });
  await page.getByRole("button", { name: "Use documents", exact: true }).click();
  await page.getByLabel("Your question").fill("How does the heliostat inspection begin?");
  const response = page.waitForResponse((row) => row.url().endsWith("/assistant/ask") && row.request().method() === "POST");
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click();
  const result = await (await response).json() as { mode: string; answer: string; sources: { title: string; page: number }[] };
  expect(result.mode).toBe("generated");
  expect(result.sources).toHaveLength(1);
  expect(result.sources[0]?.title).toBe("Synthetic heliostat checklist");
  expect(result.sources[0]?.page).toBe(1);
  await expect(page.getByRole("list", { name: "Conversation" })).toContainText("The heliostat inspection begins with an isolation checklist.");
  await expect(page.getByText("AI reply · Verified source quotations", { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/assistant-local-ai-document-reply.png", fullPage: true });
});
