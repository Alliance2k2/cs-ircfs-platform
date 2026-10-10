import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/render";
import { REFERENCE, fieldReport, reportDetail } from "@/test/workspaceFixtures";
import { FieldReportsPage } from "./FieldReportsPage";

const API = {
  ...REFERENCE,
  "field-reports/crop/11": reportDetail,
  "field-reports": { reports: [fieldReport(), fieldReport({ id: 12, kind: "rain", source: "infrastructure", title: "Rain gauge: 400 mm", rainfall_mm: 400, crop: null, pest: null, severity: null, flags: ["unusual_value"], data_origin: "demo" })], personal_data: true, truncated: false },
};

const report = async () => within(await screen.findByRole("table")).getByRole("button", { name: /Fall armyworm on Maize/ });

describe("FieldReportsPage", () => {
  it("shows each report with its checks and origin", async () => {
    stubApi(API);
    renderWithProviders(<FieldReportsPage />);
    expect(await report()).toBeInTheDocument();
    expect(screen.getAllByText("Possible duplicate").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unusual value").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Demonstration").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute("href", "/api/v1/field-reports/export.csv?days=30");
  });

  it("sends filters to the API", async () => {
    const fetchMock = stubApi(API);
    renderWithProviders(<FieldReportsPage />);
    await report();
    await userEvent.selectOptions(screen.getByLabelText("Verification"), "unverified");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/field-reports?days=30&verification=unverified", expect.anything()));
  });

  it("needs a note to reject, then records the decision", async () => {
    const fetchMock = stubApi(API);
    renderWithProviders(<FieldReportsPage />);
    await userEvent.click(await report());
    await screen.findByRole("dialog");
    await userEvent.click(await screen.findByRole("button", { name: "Reject" }));
    expect(screen.getByLabelText("Verification note")).toHaveAttribute("aria-invalid", "true");
    await userEvent.type(screen.getByLabelText("Verification note"), "Not seen on the farm");
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/field-reports/crop/11/verification", expect.objectContaining({ method: "PATCH" })));
  });

  it("gives monitors no export and no verification", async () => {
    stubApi({ ...API, "field-reports": { reports: [fieldReport({ reporter: "+25078•••0001" })], personal_data: false, truncated: false } });
    renderWithProviders(<FieldReportsPage />, { session: { account: null, role: "citizen_science_monitor", development: false } });
    await userEvent.click(await report());
    await screen.findByRole("dialog");
    expect(screen.queryByRole("link", { name: "Export CSV" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark verified" })).not.toBeInTheDocument();
    expect(screen.getByText(/Phone numbers are masked/)).toBeInTheDocument();
  });
});
