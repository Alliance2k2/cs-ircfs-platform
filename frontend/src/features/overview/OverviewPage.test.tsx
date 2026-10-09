import { screen, within } from "@testing-library/react";
import { overview } from "@/test/fixtures";
import { renderWithProviders, stubApi } from "@/test/render";
import { OverviewPage } from "./OverviewPage";

// Leaflet and Recharts need a real browser; they are checked by the build and screenshots.
vi.mock("@/components/maps/SectorMap", () => ({ default: () => <div>mapbox map</div> }));
vi.mock("@/components/charts/SchemeChart", () => ({ default: () => <div>chart</div> }));

const OPTIONS = { "irrigation-schemes": [{ id: 1, name: "PADAB", is_active: true }], sectors: [{ id: 1, name: "Ngeruka" }] };

describe("OverviewPage", () => {
  it("shows every metric with its meaning and the priority queue", async () => {
    stubApi({ "analytics/executive-overview": overview(), ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("article", { name: "Citizen reports" })).toHaveTextContent("126");
    expect(screen.getByRole("article", { name: "Rainfall, 7 days" })).toHaveTextContent("No data");
    const actions = screen.getByRole("region", { name: "Priority actions" });
    expect(within(actions).getByText("PADAB Pumping Station 1 is offline")).toBeInTheDocument();
    expect(within(actions).getByText("Critical")).toBeInTheDocument();
    expect(screen.queryByText(/These figures are invented/)).not.toBeInTheDocument();
  });

  it("labels demonstration data", async () => {
    stubApi({ "analytics/executive-overview": overview({ demo_mode: true }), ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("note")).toHaveTextContent("Demonstration data");
  });

  it("explains that the action queue is for district staff", async () => {
    stubApi({ "analytics/executive-overview": overview({ priority_actions: null }), ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText(/visible to district officers/)).toBeInTheDocument();
  });

  it("shows the reason yield achievement is not calculated", async () => {
    stubApi({ "analytics/executive-overview": overview(), ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    const schemes = await screen.findByRole("region", { name: "PADAB and APEFA Solar" });
    expect(within(schemes).getByText("Not calculated.")).toBeInTheDocument();
  });

  it("passes filters from the address bar to the API", async () => {
    const fetchMock = stubApi({ "analytics/executive-overview": overview(), ...OPTIONS });
    renderWithProviders(<OverviewPage />, { route: "/?days=90&scheme=1" });
    await screen.findByRole("article", { name: "Citizen reports" });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/analytics/executive-overview?days=90&scheme_id=1", expect.anything());
  });

  it("asks for a Mapbox token instead of showing a broken map", async () => {
    stubApi({ "analytics/executive-overview": overview(), "public/map-config": { mapbox_token: null, style: null }, ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText(/MAPBOX_ACCESS_TOKEN/)).toBeInTheDocument();
  });

  it("shows the Mapbox map when a public token is configured", async () => {
    stubApi({ "analytics/executive-overview": overview(), "public/map-config": { mapbox_token: "pk.test", style: null }, ...OPTIONS });
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("mapbox map")).toBeInTheDocument();
  });

  it("offers a retry when the overview fails", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ detail: "Database operation failed" }), { status: 500 }));
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database operation failed");
  });
});
