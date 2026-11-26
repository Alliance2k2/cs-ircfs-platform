import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { AssistantPage } from "./AssistantPage";

const config = { generation_enabled: false, retrieval_mode: "bm25", uploads_enabled: false };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

it("localizes the welcome and question suggestions with the interface language", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(config));
  renderWithProviders(<AssistantPage />, { lang: "rw" });
  expect(screen.getByRole("heading", { name: "Reka tubisuzume hamwe." })).toBeInTheDocument();
  const suggestion = screen.getByRole("button", { name: "Nahindura nte ururimi rwa USSD?" });
  await userEvent.click(suggestion);
  expect(screen.getByLabelText("Ikibazo cyawe")).toHaveValue("Nahindura nte ururimi rwa USSD?");
  expect(screen.getByText(/Ntushyire amakuru bwite/)).toBeInTheDocument();
});

it("renders cited excerpts as text and clears conversation", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => String(input).endsWith("assistant/config") ? json(config) : new Response(JSON.stringify({ answer: "<script>unsafe()</script> [field-ussd]", mode: "documents", sources: [{ id: "field-ussd", title: "USSD", text: "Use option 0.", reference: "docs/guide.md", revision: "abc" }] }), { status: 200 }));
  renderWithProviders(<AssistantPage />);
  await userEvent.type(screen.getByLabelText("Your question"), "USSD language");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  expect(await screen.findByText("<script>unsafe()</script> [field-ussd]")).toBeVisible();
  expect(document.querySelector("script")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "New chat" }));
  expect(screen.queryByText("<script>unsafe()</script> [field-ussd]")).not.toBeInTheDocument();
});

it("keeps the question when a request fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => String(input).endsWith("assistant/config") ? json(config) : json({ detail: "Please try later" }, 503));
  renderWithProviders(<AssistantPage />);
  await userEvent.type(screen.getByLabelText("Your question"), "rainfall validation");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Please try later");
  await waitFor(() => expect(screen.getByLabelText("Your question")).toBeEnabled());
  expect(screen.getByLabelText("Your question")).toHaveValue("rainfall validation");
});

it("sends bounded user context and explicit language without persisting the conversation", async () => {
  const requests: unknown[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("assistant/config")) return json(config);
    requests.push(JSON.parse(String(init?.body)));
    return new Response(JSON.stringify({ answer: "Use option 0. [field-ussd]", mode: "documents", sources: [] }), { status: 200 });
  });
  renderWithProviders(<AssistantPage />);
  await userEvent.click(screen.getByText("Chat options"));
  await userEvent.selectOptions(screen.getByLabelText("Question language"), "rw");
  await userEvent.type(screen.getByLabelText("Your question"), "USSD language");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await screen.findByText("Use option 0. [field-ussd]");
  await userEvent.type(screen.getByLabelText("Your question"), "What about returning callers?");
  await userEvent.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await waitFor(() => expect(requests).toHaveLength(2));
  expect(requests[1]).toEqual({ question: "What about returning callers?", language: "rw", history: ["USSD language"] });
  await userEvent.click(screen.getByRole("button", { name: "New chat" }));
  expect(screen.queryByRole("button", { name: "Copy answer" })).not.toBeInTheDocument();
});

it("records only categorical feedback and reports clipboard errors", async () => {
  const user = userEvent.setup();
  vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("not available"));
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => String(input).endsWith("assistant/config") ? json(config) : new Response(JSON.stringify(String(input).endsWith("feedback") ? { status: "recorded" } : { answer: "Cited answer [source]", mode: "documents", sources: [] }), { status: 200 }));
  renderWithProviders(<AssistantPage />);
  await user.type(screen.getByLabelText("Your question"), "USSD language");
  await user.click(screen.getByRole("button", { name: /^Ask assistant$/ }));
  await user.click(await screen.findByRole("button", { name: "Copy answer" }));
  expect(await screen.findByText(/Clipboard unavailable/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: /^Helpful$/ }));
  expect(await screen.findByText(/Feedback recorded without/)).toBeVisible();
  expect(JSON.parse(String(fetch.mock.calls.at(-1)?.[1]?.body))).toEqual({ vote: "helpful" });
});

it("restores an earlier chat from page-only history", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => json(String(input).endsWith("assistant/config") ? config : { answer: "Use option 0. [field-ussd]", mode: "documents", sources: [] }));
  renderWithProviders(<AssistantPage />);
  await user.type(screen.getByLabelText("Your question"), "USSD language");
  await user.click(screen.getByRole("button", { name: "Ask assistant" }));
  await screen.findByText("Use option 0. [field-ussd]");
  await user.click(screen.getByRole("button", { name: "New chat" }));
  await user.click(screen.getByLabelText("Conversation history"));
  await user.click(screen.getByRole("button", { name: "USSD language" }));
  expect(screen.getByText("Use option 0. [field-ussd]")).toBeVisible();
});

it("blocks sending when settings fail and recovers on retry", async () => {
  let available = false;
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => available ? json(config) : json({ detail: "Unavailable" }, 503));
  renderWithProviders(<AssistantPage />);
  await screen.findByText("Could not load assistant settings.");
  await user.type(screen.getByLabelText("Your question"), "USSD language");
  expect(screen.getByRole("button", { name: "Ask assistant" })).toBeDisabled();
  available = true;
  await user.click(screen.getByRole("button", { name: "Retry settings" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Ask assistant" })).toBeEnabled());
});
