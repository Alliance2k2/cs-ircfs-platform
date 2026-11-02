import { fieldReportDetailSchema } from "@/services/api/workspaces";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BaselineManager } from "@/features/admin/BaselineManager";
import { CorrectionForm } from "@/features/field-reports/CorrectionForm";
import { renderWithProviders, stubApi } from "@/test/render";
import { fieldReport } from "@/test/workspaceFixtures";

it("creates an unapproved sourced target with explicit crop, season, year and unit", async () => {
  const requests = stubApi({ "scheme-baselines": [] });
  renderWithProviders(<BaselineManager schemes={[{ id: 1, name: "PADAB" }]} />);
  await userEvent.selectOptions(screen.getByLabelText("Irrigation scheme"), "1");
  await userEvent.type(screen.getByLabelText(/^Crop/), "Rice");
  await userEvent.type(screen.getByLabelText(/^Agricultural season/), "A");
  await userEvent.type(screen.getByLabelText(/^Reference year/), "2026");
  await userEvent.type(screen.getByLabelText(/^Expected yield/), "4000");
  await userEvent.selectOptions(screen.getByLabelText("Measurement unit"), "kg/ha");
  await userEvent.type(screen.getByLabelText(/^Official source/), "District study");
  await userEvent.type(screen.getByLabelText(/^Source document reference/), "Table 2");
  await userEvent.click(screen.getByRole("button", { name: "Save unapproved version" }));
  await waitFor(() => expect(requests).toHaveBeenCalledWith("/api/v1/scheme-baselines", expect.objectContaining({
    method: "POST", body: JSON.stringify({ scheme_id: 1, crop_type: "Rice", season: "A", reference_year: 2026,
      expected_yield: 4000, yield_unit: "kg/ha", official_source: "District study", document_reference: "Table 2", supersedes_id: null }),
  })));
  expect(requests.mock.calls.some(([url]) => String(url).includes("/approve"))).toBe(false);
});

it("requires a date before explicitly approving an official baseline", async () => {
  const requests = stubApi({ "scheme-baselines": [{ id: 7, scheme_id: 1, crop_type: "Rice", season: "A", reference_year: 2026,
    expected_yield: 4, yield_unit: "t/ha", official_source: "Study", document_reference: "p.2", data_origin: "import",
    verification_status: "unverified", approved_at: null, supersedes_id: null }] });
  renderWithProviders(<BaselineManager schemes={[{ id: 1, name: "PADAB" }]} />);
  const approve = await screen.findByRole("button", { name: "Approve official target" });
  expect(approve).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Date of approval"), "2026-01-01");
  await userEvent.click(approve);
  await waitFor(() => expect(requests).toHaveBeenCalledWith("/api/v1/scheme-baselines/7/approve", expect.objectContaining({
    method: "POST", body: JSON.stringify({ approved_at: "2026-01-01" }),
  })));
});

it("submits a corrected measurement as a replacement with a reason", async () => {
  const requests = stubApi({ "field-reports/crop/1/corrections": { id: 2 } });
  const saved = vi.fn();
  renderWithProviders(<CorrectionForm onSaved={saved} report={fieldReportDetailSchema.parse({ ...fieldReport({ id: 1, source: "crop", crop: "Rice" }),
    notes: null, latitude: null, longitude: null, case: null, verification_history: [],
    cultivated_area_hectares: 2, harvested_area_hectares: 1, season: "A", reference_year: 2026,
    observation_type: "measured", data_source: "Scale", harvest_date: "2026-08-01", reported_tons: 3,
  })} />);
  await userEvent.clear(screen.getByLabelText("Observed harvest quantity"));
  await userEvent.type(screen.getByLabelText("Observed harvest quantity"), "2500");
  await userEvent.selectOptions(screen.getByLabelText("Measurement unit"), "kg");
  await userEvent.type(screen.getByLabelText(/^Correction reason/), "Reweighed on calibrated scale");
  await userEvent.click(screen.getByRole("button", { name: "Save corrected report" }));
  await waitFor(() => expect(saved).toHaveBeenCalled());
  const sent = requests.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(sent?.[1]?.body))).toMatchObject({ reason: "Reweighed on calibrated scale",
    changes: { observed_quantity: 2500, harvest_unit: "kg", reported_harvest_tons: null } });
});
