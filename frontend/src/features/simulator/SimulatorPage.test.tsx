import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SimulatorPage } from "./SimulatorPage";
import { renderWithProviders } from "@/test/render";

it("protects an in-flight answer and caller until the next prompt arrives", async () => {
  let finishPrompt!: (response: Response) => void;
  const pending = new Promise<Response>((resolve) => { finishPrompt = resolve; });
  const reply = (response: string) => new Response(JSON.stringify({ response, english: response }), { status: 200 });
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(reply("CON Main menu: Report rainfall"))
    .mockImplementationOnce(() => pending)
    .mockResolvedValueOnce(reply("END Recorded 37.5 mm"));
  renderWithProviders(<SimulatorPage />);
  await userEvent.click(screen.getByRole("button", { name: "Dial *801#" }));
  const answer = await screen.findByLabelText("Your answer");
  await userEvent.type(answer, "3");
  await userEvent.click(screen.getAllByRole("button", { name: "Send" })[0]!);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(answer).toBeDisabled();
  expect(screen.getByLabelText("Caller phone number")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Hang up" })).toBeDisabled();
  await act(async () => { finishPrompt(reply("CON Enter today's rainfall (mm), e.g. 12")); });
  await waitFor(() => expect(answer).toBeEnabled());
  expect(answer).toHaveValue("");
  await userEvent.type(answer, "37.5");
  await userEvent.click(screen.getAllByRole("button", { name: "Send" })[0]!);
  await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith("/api/v1/simulator/ussd",
    expect.objectContaining({ body: expect.stringContaining('"text":"3*37.5"') })));
  let finishRedial!: (response: Response) => void;
  fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { finishRedial = resolve; }));
  await userEvent.click(await screen.findByRole("button", { name: "New session" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Session ended" })).toBeDisabled());
  await act(async () => { finishRedial(reply("CON Main menu")); });
});

it("starts a separate session when the caller changes", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    new Response(JSON.stringify({ response: "CON Main menu", english: "Main menu" }), { status: 200 }),
  );
  renderWithProviders(<SimulatorPage />);
  await userEvent.click(screen.getByRole("button", { name: "Dial *801#" }));
  await screen.findByLabelText("Your answer");
  const caller = screen.getByLabelText("Caller phone number");
  await userEvent.clear(caller);
  await userEvent.type(caller, "+250788777002");
  await userEvent.click(screen.getByRole("button", { name: "Dial *801#" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  const first = JSON.parse(String(fetchMock.mock.calls[0]![1]?.body));
  const second = JSON.parse(String(fetchMock.mock.calls[1]![1]?.body));
  expect(second.phoneNumber).toBe("+250788777002");
  expect(second.text).toBe("");
  expect(second.sessionId).not.toBe(first.sessionId);
});
