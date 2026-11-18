import { screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { KnowledgePanel } from "./KnowledgePanel";

it("loads pending sources, previews untrusted text and requires a review reference", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(JSON.stringify(String(input).endsWith("preview") ? [{ page: 2, heading: "Pump", text: "<img src=x onerror=alert(1)>" }] : [{ document_id: "d", version_id: "v", title: "Fixture pump", language: "en", classification: "engineering", status: "pending", revision: 1, roles: ["administrator"], sector_ids: [] }]), { status: 200 }));
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
