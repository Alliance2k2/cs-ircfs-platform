import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/render";
import { ReportingActivity } from "./ReportingActivity";

const fixture = { start: "2026-11-10", end: "2026-11-11", previous_start: "2026-11-08", previous_end: "2026-11-09", reports: 12, previous_reports: 9, change: 3, verified_reports: 0, located_reports: 6, demo_mode: false };

it("sends selected receipt filters without treating zero verified reports as missing", async () => {
  const fetch = stubApi({ "analytics/reporting-activity": fixture, cells: [{ id: 40, name: "Gihembe", sector_id: 1 }], cooperatives: [{ id: 7, name: "Test cooperative", sector_id: 1 }] });
  renderWithProviders(<ReportingActivity filters={{ days: 30, sectorId: 1, schemeId: 2 }} />);
  expect(await screen.findByText("Change in reports received: +3")).toBeInTheDocument();
  expect(screen.getByText("Verified reports").nextElementSibling).toHaveTextContent("0");
  await userEvent.selectOptions(screen.getByLabelText("Cell"), "40");
  await userEvent.selectOptions(screen.getByLabelText("Cooperative"), "7");
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("cell_id=40&cooperative_id=7"))).toBe(true));
  expect(screen.getByText(/not an agricultural impact estimate/)).toBeInTheDocument();
});

it("does not request the staff-only cooperative directory for monitors", async () => {
  const fetch = stubApi({ "analytics/reporting-activity": fixture, cells: [] });
  renderWithProviders(<ReportingActivity filters={{ days: 30, sectorId: null, schemeId: null }} />, { session: { account: null, role: "citizen_science_monitor", development: false } });
  await screen.findByText("Reports received");
  expect(screen.queryByLabelText("Cooperative")).not.toBeInTheDocument();
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/cooperatives"))).toBe(false);
});
