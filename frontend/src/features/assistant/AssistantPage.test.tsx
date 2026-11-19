import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { AssistantPage } from "./AssistantPage";

it("renders cited excerpts as text and clears conversation", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ answer: "<script>unsafe()</script> [field-ussd]", mode: "documents", sources: [{ id: "field-ussd", title: "USSD", text: "Use option 0.", reference: "docs/guide.md", revision: "abc" }] }), { status: 200 }));
  renderWithProviders(<AssistantPage />);
  await userEvent.type(screen.getByLabelText("Your question"), "USSD language");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  expect(await screen.findByText("<script>unsafe()</script> [field-ussd]")).toBeVisible();
  expect(document.querySelector("script")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Clear conversation" }));
  expect(screen.queryByText("<script>unsafe()</script> [field-ussd]")).not.toBeInTheDocument();
});

it("keeps the question when a request fails", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Please try later" }), { status: 503 }));
  renderWithProviders(<AssistantPage />);
  await userEvent.type(screen.getByLabelText("Your question"), "rainfall validation");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Please try later");
  await waitFor(() => expect(screen.getByLabelText("Your question")).toBeEnabled());
  expect(screen.getByLabelText("Your question")).toHaveValue("rainfall validation");
});
