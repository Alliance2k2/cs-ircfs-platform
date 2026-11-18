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

it("sends bounded user context and explicit language without persisting the conversation", async () => {
  const requests: unknown[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
    requests.push(JSON.parse(String(init?.body)));
    return new Response(JSON.stringify({ answer: "Use option 0. [field-ussd]", mode: "documents", sources: [] }), { status: 200 });
  });
  renderWithProviders(<AssistantPage />);
  await userEvent.selectOptions(screen.getByLabelText("Question language"), "rw");
  await userEvent.type(screen.getByLabelText("Your question"), "USSD language");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await screen.findByText("Use option 0. [field-ussd]");
  await userEvent.type(screen.getByLabelText("Your question"), "What about returning callers?");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await waitFor(() => expect(requests).toHaveLength(2));
  expect(requests[1]).toEqual({ question: "What about returning callers?", language: "rw", history: ["USSD language"] });
  await userEvent.click(screen.getByRole("button", { name: "Clear conversation" }));
  expect(screen.queryByRole("button", { name: "Copy answer" })).not.toBeInTheDocument();
});

it("records only categorical feedback and reports clipboard errors", async () => {
  const user = userEvent.setup();
  vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("not available"));
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(JSON.stringify(String(input).endsWith("feedback") ? { status: "recorded" } : { answer: "Cited answer [source]", mode: "documents", sources: [] }), { status: 200 }));
  renderWithProviders(<AssistantPage />);
  await user.type(screen.getByLabelText("Your question"), "USSD language");
  await user.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await user.click(await screen.findByRole("button", { name: "Copy answer" }));
  expect(await screen.findByText(/Clipboard unavailable/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: /^Helpful$/ }));
  expect(await screen.findByText(/Feedback recorded without/)).toBeVisible();
  expect(JSON.parse(String(fetch.mock.calls.at(-1)?.[1]?.body))).toEqual({ vote: "helpful" });
});
