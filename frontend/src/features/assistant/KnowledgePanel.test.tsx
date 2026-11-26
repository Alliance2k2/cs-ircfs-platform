import { screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { KnowledgePanel } from "./KnowledgePanel";

it("loads pending sources, previews untrusted text and requires a review reference", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => String(input).endsWith("assistant/config") ? new Response(JSON.stringify({ uploads_enabled: false })) : new Response(JSON.stringify(String(input).endsWith("preview") ? [{ page: 2, heading: "Pump", text: "<img src=x onerror=alert(1)>" }] : [{ document_id: "d", version_id: "v", title: "Fixture pump", language: "en", classification: "engineering", status: "pending", revision: 1, roles: ["administrator"], sector_ids: [] }]), { status: 200 }));
  renderWithProviders(<KnowledgePanel />);
  await userEvent.click(screen.getByRole("button", { name: "Load knowledge sources" }));
  await userEvent.click(await screen.findByRole("button", { name: "Review Fixture pump revision 1" }));
  expect(await screen.findByRole("button", { name: "Approve reviewed version" })).toBeDisabled();
  await userEvent.click(screen.getByText("Page/section 2 Pump"));
  expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeVisible();
  expect(document.querySelector("img")).toBeNull();
  await userEvent.type(screen.getByLabelText("Review/approval reference"), "Synthetic fixture review");
  expect(screen.getByRole("button", { name: "Approve reviewed version" })).toBeEnabled();
});

it("shows disabled upload errors without losing the selected source", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Knowledge uploads are disabled" }), { status: 503 }));
  renderWithProviders(<KnowledgePanel />);
  await userEvent.type(screen.getByLabelText("Source title"), "Synthetic procedure");
  await userEvent.upload(screen.getByLabelText("Document file"), new File(["Synthetic pump procedure"], "guide.txt", { type: "text/plain" }));
  fireEvent.submit(screen.getByRole("form", { name: "Knowledge source upload" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Knowledge uploads are disabled");
  expect(screen.getByLabelText("Source title")).toHaveValue("Synthetic procedure");
});

it("searches source versions and recovers a failed index while uploads stay disabled", async () => {
  const user = userEvent.setup();
  let attempts = 0;
  const urls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith("assistant/config")) return new Response(JSON.stringify({ uploads_enabled: false }));
    if (url.endsWith("reindex")) {
      attempts++;
      return new Response(JSON.stringify({ detail: attempts === 1 ? "Local embedding index failed" : "Stored chunks checked; lexical retrieval ready" }), { status: attempts === 1 ? 503 : 200 });
    }
    return new Response(JSON.stringify([{ document_id: "d", version_id: "v", title: "Pump", language: "en", classification: "engineering", status: "pending", revision: 1, roles: ["administrator"], sector_ids: [], chunk_count: 2, embedding_count: 0, processing_status: attempts >= 2 ? "indexed" : "failed", processing_detail: "Synthetic status" }]));
  });
  renderWithProviders(<KnowledgePanel />);
  await user.type(screen.getByLabelText("Search source titles"), "Pump %");
  await user.selectOptions(screen.getByLabelText("Review status"), "pending");
  await user.click(screen.getByRole("button", { name: "Search sources" }));
  expect(await screen.findByText(/Index: failed/)).toBeVisible();
  expect(urls.some((url) => url.includes("q=Pump+%25&status=pending"))).toBe(true);
  await user.click(screen.getByRole("button", { name: "Recheck / reindex Pump revision 1" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Local embedding index failed");
  await user.click(screen.getByRole("button", { name: "Recheck / reindex Pump revision 1" }));
  expect(await screen.findByText(/Index: indexed/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Upload and index for review" })).toBeDisabled();
});
