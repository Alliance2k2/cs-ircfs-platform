import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Dialog, Drawer } from "@/components/ui/Overlay";
import { AdminPage } from "@/features/admin/AdminPage";
import { EvaluationPage } from "@/features/evaluation/EvaluationPage";
import { NutritionPage } from "@/features/nutrition/NutritionPage";
import { SimulatorPage } from "@/features/simulator/SimulatorPage";
import { renderWithProviders, stubApi } from "@/test/render";
import { REFERENCE } from "@/test/workspaceFixtures";

// Recharts needs a real browser; charts are covered by the build and screenshots.
vi.mock("@/features/trends/TrendChartView", () => ({ default: () => <div>chart</div> }));

const TRENDS = { "analytics/trends": { months: [] } };

describe("NutritionPage", () => {
  it("hides scores for cells with too few households", async () => {
    stubApi({
      ...TRENDS,
      "analytics/nutrition-summary": {
        households: 7, average_risk: 2.4, high_risk_households: 1, one_meal_households: 1, food_insufficient: 2, min_households_per_group: 5,
        by_cell: [
          { cell_id: 1, cell: "Rutonde", households: 5, suppressed: false, average_risk: 2.6, high_risk: 1, latitude: null, longitude: null },
          { cell_id: 2, cell: "Gihembe", households: 2, suppressed: true, average_risk: null, high_risk: null, latitude: null, longitude: null },
        ],
      },
    });
    renderWithProviders(<NutritionPage />);
    const table = await screen.findByRole("table");
    const hidden = within(table).getByRole("row", { name: /Gihembe/ });
    expect(hidden).toHaveTextContent("Hidden (too few)");
    expect(within(table).getByRole("row", { name: /Rutonde/ })).toHaveTextContent("2.6 / 5");
    expect(screen.getByText(/Fewer than 5 households/)).toBeInTheDocument();
  });
});

describe("EvaluationPage", () => {
  it("says yield achievement is not computable and lists what is missing", async () => {
    stubApi({
      evaluation: {
        generated_at: "2026-10-10T08:00:00Z", period_days: 365, method: "Counts only. No outcome is estimated.",
        questions: [{ id: 1, question: "Were the expected irrigation outcomes achieved?", section: "outcomes" }],
        schemes: [{
          scheme_id: 1, name: "PADAB", implementing_partner: "PADAB", hectares_developed: null,
          documentation: { target_tons: 75, target_source: "DEMONSTRATION VALUE", state: "demo" },
          outcomes: {
            harvest_reports: 3, reported_tons: 2, expected_tons: 4, pest_alerts: 1, severe_pest_alerts: 0, crops: [],
            yield_achievement: { value: null, computable: false, formula: "100 × observed ÷ target", requirements: [{ item: "Harvested area recorded", met: false, note: "USSD records tons only" }] },
          },
          bottlenecks: { window_days: 90, by_category: {}, flagged: [], above_baseline: [], assets_reported: 0, assets_down: 0, fault_reports: 0 },
          feedback: { grievances: 0, open: 0, resolved: 0, by_category: {} },
          downstream: { grievances: 0, open: 0 },
          evidence: { reports: 3, located_percent: 100, verified_percent: 0, rejected: 0, demo_percent: 100, months_with_reports: 1, months_in_period: 12, last_report_at: null },
        }],
      },
    });
    renderWithProviders(<EvaluationPage />);
    expect(await screen.findByText("Not computable yet")).toBeInTheDocument();
    expect(screen.getByText("Harvested area recorded")).toBeInTheDocument();
    expect(screen.getByText("Demonstration value")).toBeInTheDocument();
    expect(screen.queryByText(/%$/, { selector: ".font-heading" })).not.toBeInTheDocument();
  });
});

describe("AdminPage", () => {
  it("asks for confirmation before approving an account", async () => {
    const fetchMock = stubApi({
      ...REFERENCE,
      "auth/accounts": [{ id: 4, email: "new@example.org", full_name: "New Officer", role: "district_officer", status: "pending", created_at: "2026-10-09T08:00:00Z", sector_ids: [] }],
    });
    renderWithProviders(<AdminPage />, { session: { account: null, role: "administrator", development: false } });
    const [approve] = await screen.findAllByRole("button", { name: "Approve" });
    await userEvent.click(approve!);
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("Approve New Officer as District officer?");
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/accounts/4", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ status: "active" }) })));
  });
});

describe("SimulatorPage", () => {
  it("runs a USSD session against the simulator endpoint", async () => {
    const fetchMock = stubApi({ "simulator/ussd": { response: "CON Murakaza neza\n1. Umusaruro", english: "CON Welcome\n1. Harvest" } });
    renderWithProviders(<SimulatorPage />);
    await userEvent.click(screen.getByRole("button", { name: "Dial *801#" }));
    expect(await screen.findAllByText(/Murakaza neza/)).not.toHaveLength(0);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/simulator/ussd", expect.objectContaining({ method: "POST" }));
    expect(screen.getByLabelText("Your answer")).toBeInTheDocument();
  });
});

describe("Overlays", () => {
  function Nested() {
    const [drawer, setDrawer] = useState(true);
    const [dialog, setDialog] = useState(true);
    return (
      <Drawer open={drawer} onClose={() => setDrawer(false)} title="Case">
        <Dialog open={dialog} onClose={() => setDialog(false)} title="Confirm" actions={<button type="button">OK</button>}>Sure?</Dialog>
      </Drawer>
    );
  }

  it("closes only the top overlay on Escape", async () => {
    renderWithProviders(<Nested />);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Case" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
