import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/render";
import { REFERENCE, actNow, incidentCase } from "@/test/workspaceFixtures";
import { ActionsPage } from "./ActionsPage";

const API = {
  ...REFERENCE,
  "analytics/act-now": actNow,
  "admin/assignees": [{ id: 7, full_name: "Aline Officer", role: "district_officer", area: "Ngeruka" }],
  "cases/5/history": [],
  "cases/5": incidentCase,
};

describe("ActionsPage", () => {
  it("lists cases and grievances, most urgent first", async () => {
    stubApi(API);
    renderWithProviders(<ActionsPage />);
    const rows = await screen.findAllByRole("row");
    expect(rows[1]).toHaveTextContent("PADAB Pumping Station 1 is offline");
    expect(rows[1]).toHaveTextContent("Critical");
    expect(rows[2]).toHaveTextContent("Water Pricing");
  });

  it("filters to grievances only", async () => {
    stubApi(API);
    renderWithProviders(<ActionsPage />);
    await screen.findAllByText("Water Pricing");
    await userEvent.selectOptions(screen.getByLabelText("Type"), "grievance");
    expect(screen.queryAllByText("PADAB Pumping Station 1 is offline")).toHaveLength(0);
  });

  it("will not resolve a case without the action taken, then saves it", async () => {
    const fetchMock = stubApi(API);
    renderWithProviders(<ActionsPage />, { route: "/actions?open=infrastructure-5" });
    const drawer = await screen.findByRole("dialog", { name: "PADAB Pumping Station 1 is offline" });
    await within(drawer).findByLabelText("Status");
    await userEvent.selectOptions(within(drawer).getByLabelText("Status"), "resolved");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(within(drawer).getByLabelText(/Action taken/)).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);

    await userEvent.type(within(drawer).getByLabelText(/Action taken/), "Motor rewound");
    await userEvent.selectOptions(within(drawer).getByLabelText("Assigned to"), "7");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(true));
    const [url, init] = fetchMock.mock.calls.find(([, call]) => call?.method === "PATCH")!;
    expect(url).toBe("/api/v1/cases/5");
    expect(JSON.parse(String(init!.body))).toMatchObject({ status: "resolved", assigned_to_account_id: 7, action_taken: "Motor rewound" });
  });

  it("keeps closing the loop disabled until the case is resolved", async () => {
    stubApi(API);
    renderWithProviders(<ActionsPage />, { route: "/actions?open=infrastructure-5" });
    await screen.findByRole("dialog");
    expect(await screen.findByRole("button", { name: "Tell the community by SMS" })).toBeDisabled();
  });
});
