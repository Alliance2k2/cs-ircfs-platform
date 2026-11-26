import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, stubApi } from "@/test/render";
import { MapPage } from "./MapPage";

it("keeps recorded points searchable and readable when map tiles are unavailable", async () => {
  stubApi({
    "public/map-config": { mapbox_token: null, style: null },
    "map-data": { features: [
      { id: "a", feature_type: "irrigation", name: "Test pump", latitude: -2.3, longitude: 30.2, status: "offline", scheme_id: 1, details: null },
      { id: "b", feature_type: "rainfall", name: "Dry gauge", latitude: -2.31, longitude: 30.21, status: "0 mm", scheme_id: 1, details: null },
    ], spatial_available: false, unlocated_reports: 2 },
  });
  renderWithProviders(<MapPage />, { session: { account: null, role: "cooperative_leader", development: false } });
  await screen.findByText(/MAPBOX_ACCESS_TOKEN/);
  expect(screen.getAllByText("0 mm").length).toBeGreaterThan(0);
  await userEvent.type(screen.getByLabelText("Search observation name or status"), "pump");
  await waitFor(() => expect(screen.queryByText("Dry gauge")).not.toBeInTheDocument());
  expect(screen.getAllByText("Test pump").length).toBeGreaterThan(0);
  await userEvent.clear(screen.getByLabelText("Search observation name or status"));
  await userEvent.type(screen.getByLabelText("Search observation name or status"), "no match");
  expect(await screen.findByText("No recorded points match these layers and search.")).toBeInTheDocument();
});
