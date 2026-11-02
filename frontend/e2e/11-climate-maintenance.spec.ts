import { asRole, expect, expectToast } from "./fixtures";

const test = asRole("admin");

test("approve a rainfall reference and record a timed outage repair", async ({ page }) => {
  // Synthetic records live only in the disposable E2E database.
  const first = new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10);
  const last = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  const today = new Date().toISOString().slice(0, 10);
  const cells = await (await page.request.get("/api/v1/cells")).json();
  const cell = cells[0];
  for (const [day, mm] of [[first, 10], [last, 20]] as const) {
    const response = await page.request.post("/api/v1/irrigation-reports", { data: {
      cell_id: cell.id, observation_date: day, gauge_code: "E2E synthetic gauge", rainfall_mm: mm, data_source: "Synthetic E2E gauge sheet",
    } });
    expect(response.status()).toBe(201);
    const row = await response.json();
    expect((await page.request.patch(`/api/v1/field-reports/infrastructure/${row.id}/verification`, { data: { status: "verified" } })).status()).toBe(200);
  }
  await page.goto("/app/climate");
  await page.getByLabel("Rainfall period start").fill(first);
  await page.getByLabel("Rainfall period end").fill(last);
  await page.getByLabel("Rainfall location").selectOption(`sector:${cell.sector_id}`);
  await page.getByText("Historical reference documents and approval").click();
  await page.getByLabel(/^Reference first year/).fill("1991");
  await page.getByLabel(/^Reference last year/).fill("2020");
  await page.getByLabel(/^Historical mean total/).fill("20");
  await page.getByLabel(/^Rainfall reference source/).fill("Synthetic E2E reference only");
  await page.getByLabel(/^Rainfall source document/).fill("E2E fixture table 1");
  await page.getByRole("button", { name: "Save rainfall reference" }).click();
  await expectToast(page, "Reference saved");
  const refs = await (await page.request.get("/api/v1/climate/references")).json();
  const reference = refs.find((r: { source: string }) => r.source === "Synthetic E2E reference only");
  await page.getByLabel("Rainfall reference approval date").fill(today);
  await page.getByRole("button", { name: `Approve rainfall reference #${reference.id}` }).click();
  await expect(page.getByRole("button", { name: `Approve rainfall reference #${reference.id}` })).toHaveCount(0);
  await page.getByLabel("Historical rainfall reference", { exact: true }).selectOption(String(reference.id));
  await expect(page.getByRole("status").filter({ hasText: "Rainfall anomaly:" })).toContainText("50%");

  const assetResponse = await page.request.post("/api/v1/scheme-assets", { data: {
    name_en: "E2E synthetic maintenance pump", name_rw: "E2E synthetic maintenance pump", cell_id: cell.id, asset_type: "pump",
  } });
  expect(assetResponse.status()).toBe(201);
  const asset = await assetResponse.json();
  await page.goto("/app/irrigation");
  await page.getByLabel("Maintenance inventory asset").selectOption(String(asset.id));
  await page.getByLabel(/^Outage start/).fill(`${first}T08:00`);
  await page.getByLabel(/^Outage description/).fill("Synthetic motor failure");
  await page.getByLabel(/^Outage source/).fill("Synthetic E2E operator sheet");
  await page.getByRole("button", { name: "Save outage" }).click();
  await expectToast(page, "Maintenance record saved");
  const history = await (await page.request.get("/api/v1/irrigation/maintenance")).json();
  const outage = history.assets.find((a: { id: number }) => a.id === asset.id).outages[0];
  await page.getByLabel("Related open outage").selectOption(String(outage.id));
  await page.getByLabel("Maintenance type").selectOption("repair");
  await page.getByLabel(/^Maintenance performed/).fill(`${first}T14:00`);
  await page.getByLabel(/^Maintenance action/).fill("Synthetic motor replacement and test");
  await page.getByLabel(/^Maintenance source/).fill("Synthetic E2E repair sheet");
  await page.getByRole("checkbox", { name: "Service restored by this repair" }).check();
  await page.getByRole("button", { name: "Save maintenance" }).click();
  const table = page.getByRole("table", { name: "Recorded asset downtime" });
  await expect(table.getByRole("row").filter({ hasText: "E2E synthetic maintenance pump" })).toContainText("6 hours");
});
