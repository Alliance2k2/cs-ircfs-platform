import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { renderWithProviders } from "@/test/render";
import { DocumentWorkspace } from "./DocumentWorkspace";

it("selects reviewed documents and keeps gated uploads visible without enabling them", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(JSON.stringify(String(input).endsWith("assistant/config") ? { uploads_enabled: false } : [
    { reference: "packaged:guide", title: "USSD guide", status: "packaged", language: "en" },
    { reference: "knowledge:fixture", title: "Reviewed pump procedure", status: "approved", language: "en" },
  ])));
  function Harness() {
    const [selected, setSelected] = useState<string[]>([]);
    return <DocumentWorkspace selected={selected} onChange={setSelected} isAdmin uploadsEnabled={false} onClose={() => undefined} />;
  }
  renderWithProviders(<Harness />);
  await user.click(await screen.findByRole("checkbox", { name: /Reviewed pump procedure/ }));
  expect(screen.getByText(/1 selected/)).toBeVisible();
  await user.type(screen.getByLabelText("Find a document"), "pump");
  expect(screen.queryByRole("checkbox", { name: /USSD guide/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Upload & review" }));
  expect(screen.getByRole("heading", { name: "Manage knowledge sources" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Upload and index for review" })).toBeDisabled();
});
