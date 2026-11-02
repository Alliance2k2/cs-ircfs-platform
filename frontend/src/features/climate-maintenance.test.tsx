import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RainfallRecords } from "@/features/climate/RainfallRecords";
import { MaintenancePanel } from "@/features/irrigation/MaintenancePanel";
import { renderWithProviders, stubApi } from "@/test/render";
import { REFERENCE } from "@/test/workspaceFixtures";

vi.mock("@/features/climate/RainfallChart", () => ({ default: () => <div>rainfall chart</div> }));
const summary = {
  daily: [{ date: "2026-10-01", mean_mm: 0, gauges: 1, verified_gauges: 1 }, { date: "2026-10-02", mean_mm: null, gauges: 0, verified_gauges: 0 }],
  observed_days: 1, missing_days: 1, gauges: 1, complete_verified_gauges: 0, coverage_percent: 50,
  partial_total_mm: 0, verified_complete_total_mm: null, legacy_date_reports: 0, unknown_gauge_reports: 0, method: "Missing days are null.",
};
const rainfall = {
  start: "2026-10-01", end: "2026-10-02", generated_at: "2026-10-03T00:00:00Z", summary, seven_day: summary,
  anomaly: { status: "missing_reference", difference_mm: null, percent: null, reference: null }, by_sector: [], by_scheme: [],
};
const history = {
  start: "2026-10-01", end: "2026-10-02", as_of: "2026-10-02T22:00:00Z", method: "Recorded outage intervals only.",
  assets: [{ id: 1, name: "Test pump", scheme_id: 1, scheme: "PADAB", cell_id: 40,
    recorded_downtime_hours: null, outage_count: 0, open_outages: 0, recurrent_categories: [], outages: [], maintenance: [] }],
};

it("distinguishes a recorded zero from a missing rainfall day", async () => {
  stubApi({ ...REFERENCE, "climate/references": [], "climate/rainfall": rainfall });
  renderWithProviders(<RainfallRecords />);
  const table = await screen.findByRole("table", { name: "Daily rainfall observations" });
  expect(within(table).getByRole("row", { name: /2026-10-01/ })).toHaveTextContent("0 mm");
  expect(within(table).getByRole("row", { name: /2026-10-02/ })).toHaveTextContent("Missing");
  expect(screen.getByText(/Rainfall anomaly:/)).toHaveTextContent("missing reference");
  expect(screen.getByText(/Partial totals are not complete/)).toBeInTheDocument();
});

it("creates a sourced rainfall reference without automatically approving it", async () => {
  const requests = stubApi({ ...REFERENCE, "climate/references": [], "climate/rainfall": rainfall });
  renderWithProviders(<RainfallRecords />, { session: { account: null, role: "administrator", development: false } });
  await screen.findByRole("option", { name: "Sector: Ngeruka" });
  await userEvent.selectOptions(screen.getByLabelText("Rainfall location"), "sector:1");
  await userEvent.click(screen.getByText("Historical reference documents and approval"));
  await userEvent.type(screen.getByLabelText(/^Reference first year/), "1991");
  await userEvent.type(screen.getByLabelText(/^Reference last year/), "2020");
  await userEvent.type(screen.getByLabelText(/^Historical mean total/), "20");
  await userEvent.type(screen.getByLabelText(/^Rainfall reference source/), "Synthetic reference");
  await userEvent.type(screen.getByLabelText(/^Rainfall source document/), "Table 1");
  await userEvent.click(screen.getByRole("button", { name: "Save rainfall reference" }));
  await waitFor(() => expect(requests.mock.calls.some(([url, init]) => String(url) === "/api/v1/climate/references" && init?.method === "POST")).toBe(true));
  const sent = requests.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(sent?.[1]?.body))).toMatchObject({ sector_id: 1, scheme_id: null, mean_rainfall_mm: 20, reference_start_year: 1991, reference_end_year: 2020 });
  expect(requests.mock.calls.some(([url]) => String(url).includes("/approve"))).toBe(false);
});

it("shows unknown downtime until an outage is recorded and submits Kigali timestamps", async () => {
  const requests = stubApi({ "irrigation/maintenance": history, "irrigation/outages": { id: 1 } });
  renderWithProviders(<MaintenancePanel />);
  const table = await screen.findByRole("table", { name: "Recorded asset downtime" });
  expect(within(table).getByText("Unknown")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Maintenance inventory asset"), "1");
  await userEvent.type(screen.getByLabelText(/^Outage start/), "2026-10-01T08:00");
  await userEvent.type(screen.getByLabelText(/^Outage description/), "Motor stopped");
  await userEvent.type(screen.getByLabelText(/^Outage source/), "Operator sheet");
  await userEvent.click(screen.getByRole("button", { name: "Save outage" }));
  await waitFor(() => expect(requests).toHaveBeenCalledWith("/api/v1/irrigation/outages", expect.objectContaining({ method: "POST" })));
  const sent = requests.mock.calls.find(([url, init]) => String(url).endsWith("/outages") && init?.method === "POST");
  expect(JSON.parse(String(sent?.[1]?.body))).toMatchObject({ asset_id: 1, cell_id: 40, started_at: "2026-10-01T06:00:00.000Z", category: "technical", source: "Operator sheet" });
});

it("keeps maintenance writes out of the monitor workspace", async () => {
  stubApi({ "irrigation/maintenance": history });
  renderWithProviders(<MaintenancePanel />, { session: { account: null, role: "citizen_science_monitor", development: false } });
  await screen.findByRole("table");
  await userEvent.selectOptions(screen.getByLabelText("Maintenance inventory asset"), "1");
  expect(screen.queryByRole("button", { name: "Save outage" })).not.toBeInTheDocument();
});
