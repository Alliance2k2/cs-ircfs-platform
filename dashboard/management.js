// Platform Management. API access, sign-in session and language come from shared.js (window.CS).
const { API, apiFetch } = window.CS;
let activeModule = "users";
let liveMode = false;
let renderedRows = [];
let renderedLive = false;
let currentPage = 1;
const PAGE_SIZE = 10;

const modules = {
  users: {
    title: "Users", subtitle: "Manage the people who report, monitor, and use district information.", add: "+ Add user", search: "Search users...",
    cards: [["Registered users", "250", "Across 3 pilot cooperatives", ""], ["Farmers", "208", "Community reporters", "blue"], ["Citizen monitors", "24", "Field observation team", "gold"], ["Active this month", "186", "74% participation", "coral"]],
    columns: ["User", "Role", "Cooperative", "Location", "Status"],
    rows: [["Aline Umutoni", "AU", "farmer", "Koperative Mwesa", "Nyamata", "active"], ["Jean Habineza", "JH", "citizen science monitor", "Mwesa Data Team", "Nyamata", "active"], ["Claudine Mukamana", "CM", "cooperative leader", "APEFA Growers", "Ngeruka", "active"], ["David Niyonzima", "DN", "district planner", "Bugesera District", "Nyamata", "active"]],
  },
  schemes: {
    title: "Irrigation schemes", subtitle: "Manage irrigation investments and verify their outcomes.", add: "+ Add scheme", search: "Search schemes...",
    cards: [["Active schemes", "2", "Pilot investments", ""], ["PADAB coverage", "650 ha", "Verify official figure", "blue"], ["Infrastructure assets", "2", "Pumping stations recorded", "gold"], ["Outcome status", "Watch", "Needs verified field data", "coral"]],
    columns: ["Scheme", "Partner", "Location", "Area", "Status"],
    rows: [["PADAB", "PD", "AfDB", "Mwesa Valley", "650 ha", "operational"], ["APEFA Solar", "AS", "APEFA", "Ngeruka & Mareba", "To verify", "operational"]],
    helper: ["Scheme data must be verified", "PADAB and APEFA figures are presentation examples until official scheme records, asset lists, and yield targets are approved."]
  },
  citizen: {
    title: "Citizen reports", subtitle: "Review crop production, harvest, pest, and disease observations.", add: "+ New report", search: "Search citizen reports...",
    cards: [["Total reports", "1,250", "All crop observations", ""], ["Pest alerts", "27", "Need extension review", "coral"], ["Expected harvest", "418 t", "Reported by farmers", "blue"], ["High severity", "5", "Act Now priority", "gold"]],
    columns: ["Reporter", "Crop", "Observation", "Scheme", "Location", "Severity"],
    rows: [["Jean Habineza", "JH", "Maize", "Fall armyworm", "APEFA Solar", "Ngeruka", "critical"], ["Aline Umutoni", "AU", "Rice", "Planting update", "PADAB", "Nyamata", "active"], ["Claudine Mukamana", "CM", "Beans", "Expected harvest", "APEFA Solar", "Mareba", "triaged"]],
    helper: ["Citizen science creates evidence", "Reports show what is happening in the field and help planners compare real outcomes with expected irrigation benefits."]
  },
  irrigation: {
    title: "Rainfall & irrigation", subtitle: "Monitor rain gauges, water availability, pumps, canals, and faults.", add: "+ New observation", search: "Search irrigation reports...",
    cards: [["Irrigation reports", "84", "This reporting period", ""], ["Rainfall readings", "49", "Local gauge network", "blue"], ["Offline assets", "3", "Critical follow-up", "coral"], ["Operational assets", "18", "Reported this month", "gold"]],
    columns: ["Asset / observation", "Scheme", "Condition", "Rainfall", "Bottleneck", "Status"],
    rows: [["Mwesa Pump A", "MP", "PADAB", "offline", "12.5 mm", "technical", "offline"], ["Ngeruka solar pump", "NS", "APEFA Solar", "operational", "8.0 mm", "-", "operational"], ["Canal section 4", "C4", "PADAB", "faulty", "15.0 mm", "environmental", "faulty"]],
    helper: ["Water reliability is visible", "Infrastructure failures and rainfall observations become priority cases so the responsible team can act quickly."]
  },
  feedback: {
    title: "Community feedback", subtitle: "Follow every concern from community report to final response.", add: "+ New feedback", search: "Search feedback cases...",
    cards: [["Open cases", "35", "Need planner response", "coral"], ["Resolved cases", "18", "Action recorded", ""], ["Assigned cases", "12", "Owners identified", "blue"], ["Median response", "1.8d", "Pilot indicator", "gold"]],
    columns: ["Case", "Category", "Scheme", "Location", "Assigned to", "Status"],
    rows: [["FB-058", "F5", "Water pricing", "PADAB", "Nyamata", "District Planner", "open"], ["FB-052", "F5", "Canal access", "APEFA Solar", "Ngeruka", "Water Officer", "triaged"], ["FB-041", "F4", "Input distribution", "PADAB", "Mwesa", "Cooperative Lead", "resolved"]],
    helper: ["Closing the loop builds trust", "Every community issue needs an owner, action record, and response. Anonymous feedback remains protected."]
  },
  accounts: {
    title: "Accounts", subtitle: "Approve web sign-ins and give planners and officers the right role.", add: "Refresh", search: "Search accounts...",
    cards: [["Web accounts", "12", "Signed-up people", ""], ["District planners", "3", "Can view planner data", "blue"], ["Administrators", "1", "Manage the platform", "gold"], ["Suspended", "0", "Blocked from sign-in", "coral"]],
    columns: ["Account", "Email", "Role", "Area", "Joined", "Status"],
    rows: [["David Niyonzima", "DN", "david@example.org", "district_planner", "2026-09-01", "active"], ["Grace Ingabire", "GI", "grace@example.org", "citizen_science_monitor", "2026-09-20", "active"]],
  },
  nutrition: {
    title: "Household nutrition", subtitle: "Household Nutrition Tracker answers collected through USSD option 6.", add: "+ New survey", search: "Search surveys...",
    cards: [["Households surveyed", "184", "Across pilot cells", ""], ["High stunting risk", "31", "Score 4 or 5", "coral"], ["One meal a day", "18", "Households", "gold"], ["Short of food", "52", "Until next harvest", "blue"]],
    columns: ["Survey", "Location", "Meals / day", "Varied diet", "Enough food", "Risk"],
    rows: [["NS-001", "NS", "Gihembe", "1", "no", "no", "high"], ["NS-002", "NS", "Rango", "3", "yes", "yes", "low"]],
  },
  messages: {
    title: "SMS & airtime log", subtitle: "Every message sent to citizens: advice, automatic replies, and closing-the-loop notices.", add: "Refresh", search: "Search messages...",
    cards: [["Messages sent", "1,024", "Advice, replies, closing the loop", ""], ["Closing the loop", "214", "Community notifications", "blue"], ["Irrigation advice", "306", "Scheduling assistant", "gold"], ["Automatic replies", "504", "Thank-you and local tips", "coral"]],
    columns: ["Recipient", "Message", "Purpose", "Sent", "Status"],
    rows: [["+250788550011", "SM", "Inama: imvura yabaye nke (6.1 mm mu minsi 7). Ongera kuhira ho 10%.", "irrigation schedule", "Today", "dry_run"]],
  },
  analytics: {
    title: "Analytics", subtitle: "Use validated reports to prioritise district decisions.", add: "View Act Now", search: "Search analytics...",
    cards: [["Act Now alerts", "3", "Critical and high priority", "coral"], ["Harvest performance", "71%", "Illustrative pilot trend", ""], ["Data quality", "94%", "Valid submitted reports", "blue"], ["Report coverage", "74%", "Active reporter rate", "gold"]],
    columns: ["Priority item", "Type", "Scheme", "Location", "Reported", "Priority"],
    rows: [["Mwesa Pump A offline", "MP", "Infrastructure", "PADAB", "Nyamata", "Today", "critical"], ["Fall armyworm alert", "FA", "Pest / disease", "APEFA Solar", "Ngeruka", "Today", "critical"], ["Water pricing", "WP", "Feedback", "PADAB", "Nyamata", "Yesterday", "triaged"]],
    helper: ["Analytics support, not replace, decisions", "The platform shows transparent signals. District Planners still confirm bottlenecks and decide what action to take."]
  }
};

const statusValues = new Set(["active", "open", "resolved", "triaged", "offline", "operational", "faulty", "critical", "suspended", "pending", "high", "medium", "low", "sent", "dry_run", "failed", "reference only", "assigned", "in_progress", "closed"]);
const ROLES = ["farmer", "citizen_science_monitor", "cooperative_leader", "district_officer", "district_planner", "administrator"];
let lookups = { schemes: {}, cells: {}, sectors: {} };
const initials = (name) => name.split(" ").map((word) => word[0]).join("").slice(0, 2).toUpperCase();
const slug = (value) => String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-");
const badge = (value) => `<span class="status-badge status-${slug(value)}">${escapeHtml(String(value).replaceAll("_", " "))}</span>`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);

function normalCell(value) {
  return statusValues.has(String(value).toLowerCase()) ? badge(value) : escapeHtml(value || "-");
}

function draw(data, rows, isLive = false) {
  renderedRows = rows;
  renderedLive = isLive;
  currentPage = 1;
  document.querySelector("#page-title").textContent = data.title;
  document.querySelector("#page-subtitle").textContent = data.subtitle;
  document.querySelector("#add-button").textContent = data.add;
  document.querySelector("#add-button").disabled = false;
  document.querySelector("#add-button").title = activeModule === "analytics" ? "Open the planner Act Now queue" : `Add ${data.title.toLowerCase()}`;
  document.querySelector("#table-search").placeholder = data.search;
  const cards = isLive ? data.cards.map((card, index) => [card[0], index === 0 ? rows.length.toLocaleString() : "-", index === 0 ? "Live PostgreSQL records" : "Calculated when records are entered", card[3]]) : data.cards;
  document.querySelector("#summary-row").innerHTML = cards.map((card) => `<article class="summary-card ${card[3]}"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join("");
  const hasActions = activeModule === "users" || (isLive && ["accounts", "schemes"].includes(activeModule));
  document.querySelector("#table-head").innerHTML = `<tr>${data.columns.map((column) => `<th>${column}</th>`).join("")}${hasActions ? "<th>Actions</th>" : ""}</tr>`;
  const body = document.querySelector("#table-body");
  if (!rows.length) {
    body.innerHTML = `<tr><td class="empty-row" colspan="${data.columns.length + (hasActions ? 1 : 0)}">No ${data.title.toLowerCase()} have been entered in PostgreSQL yet. Use the Add button to create the first record.</td></tr>`;
  } else if (activeModule === "users") {
    body.innerHTML = rows.map((row) => `<tr><td><div class="user-cell"><span class="mini-avatar">${escapeHtml(row[1])}</span><span><strong>${escapeHtml(row[0])}</strong><small>${escapeHtml(row[2].replaceAll("_", " "))}</small></span></div></td><td>${badge(row[2])}</td><td>${escapeHtml(row[3] || "—")}</td><td>${escapeHtml(row[4] || "—")}</td><td>${badge(row[5])}</td><td><button class="row-action" data-action="edit" data-id="${Number(row[6])}">Edit</button><button class="row-action danger" data-action="delete" data-id="${Number(row[6])}">Delete</button></td></tr>`).join("");
  } else if (hasActions && activeModule === "accounts") {
    body.innerHTML = rows.map((row) => `<tr><td><div class="user-cell"><span class="mini-avatar">${escapeHtml(row[1])}</span><strong>${escapeHtml(row[0])}</strong></div></td><td>${escapeHtml(row[2])}</td><td><select class="role-select" data-account="${Number(row[6])}" aria-label="Role">${ROLES.map((role) => `<option value="${role}" ${role === row[3] ? "selected" : ""}>${role.replaceAll("_", " ")}</option>`).join("")}</select></td><td><button class="row-action" data-action="account-area" data-id="${Number(row[6])}" data-sectors="${escapeHtml((row[7] || []).join(","))}" title="Choose the sectors this account works in">${escapeHtml(areaLabel(row[3], row[7]))}</button></td><td>${escapeHtml(row[4])}</td><td>${badge(row[5])}</td><td><button class="row-action ${row[5] === "active" ? "danger" : ""}" data-action="toggle-account" data-id="${Number(row[6])}" data-status="${escapeHtml(row[5])}">${row[5] === "active" ? "Suspend" : "Activate"}</button></td></tr>`).join("");
  } else {
    body.innerHTML = rows.map((row) => `<tr><td><div class="user-cell"><span class="mini-avatar">${escapeHtml(row[1])}</span><strong>${escapeHtml(row[0])}</strong></div></td>${row.slice(2, hasActions ? -1 : undefined).map(normalCell).map((value) => `<td>${value}</td>`).join("")}${hasActions ? `<td><button class="row-action" data-action="edit-scheme" data-id="${Number(row.at(-1))}">Edit figures</button></td>` : ""}</tr>`).join("");
  }
  populateFilter();
  updateVisibleRows();
}

function updateVisibleRows() {
  const term = document.querySelector("#table-search").value.trim().toLowerCase();
  const filter = document.querySelector("#table-filter").value;
  const matching = renderedRows.map((row, index) => ({ row, index })).filter(({ row }) => {
    const text = row.join(" ").toLowerCase();
    const filterValue = filterCell(row).toLowerCase();
    return (!term || text.includes(term)) && (filter === "all" || filterValue === filter);
  });
  const pages = Math.max(1, Math.ceil(matching.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, pages);
  const visibleIndexes = new Set(matching.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE).map(({ index }) => index));
  document.querySelectorAll("#table-body tr").forEach((row, index) => { row.hidden = Boolean(renderedRows[index] && !visibleIndexes.has(index)); });
  document.querySelector("#current-page").textContent = String(currentPage);
  document.querySelector("#previous-page").disabled = currentPage <= 1;
  document.querySelector("#next-page").disabled = currentPage >= pages;
  document.querySelector("#table-count").textContent = matching.length
    ? `Showing ${(currentPage - 1) * PAGE_SIZE + 1}-${Math.min(currentPage * PAGE_SIZE, matching.length)} of ${matching.length} ${renderedLive ? "PostgreSQL" : "demonstration"} records`
    : `No matching ${renderedLive ? "PostgreSQL" : "demonstration"} records`;
}

function populateFilter() {
  const select = document.querySelector("#table-filter");
  const previous = select.value;
  const values = [...new Set(renderedRows.map((row) => filterCell(row).trim()).filter(Boolean))].sort();
  select.replaceChildren(new Option("All records", "all"), ...values.map((value) => new Option(value.replaceAll("_", " "), value.toLowerCase())));
  select.value = values.some((value) => value.toLowerCase() === previous) ? previous : "all";
}

function filterCell(row) {
  if (activeModule === "users" || activeModule === "accounts") return String(row[5] ?? "");
  if (activeModule === "schemes" && renderedLive) return String(row.at(-2) ?? "");
  return String(row.at(-1) ?? "");
}

function sampleRows(module) { return modules[module].rows; }

const schemeName = (id) => (id ? lookups.schemes[id] || `Scheme #${id}` : "-");
const cellName = (id) => (id ? lookups.cells[id] || `Cell #${id}` : "-");

async function loadLookups() {
  const [schemes, cells, sectors] = await Promise.all(["irrigation-schemes", "locations/cells", "locations/sectors"].map((path) => apiFetch(path).then((r) => (r.ok ? r.json() : [])).catch(() => [])));
  const sectorNames = Object.fromEntries(sectors.map((sector) => [sector.id, sector.name]));
  lookups = {
    schemes: Object.fromEntries(schemes.map((scheme) => [scheme.id, scheme.name])),
    cells: Object.fromEntries(cells.map((cell) => [cell.id, `${cell.name}${sectorNames[cell.sector_id] ? ` (${sectorNames[cell.sector_id]})` : ""}`])),
    sectors: sectorNames,
  };
}

async function fetchLiveRows(module) {
  const endpoints = { users: "users", schemes: "irrigation-schemes", citizen: "citizen-reports", irrigation: "irrigation-reports", feedback: "feedback", analytics: "analytics/act-now", accounts: "auth/accounts", nutrition: "nutrition-surveys", messages: "advisory/messages" };
  const response = await apiFetch(endpoints[module]);
  if (response.status === 403) throw Object.assign(new Error("Your role cannot open this section"), { forbidden: true });
  if (!response.ok) throw new Error("API request failed");
  const records = await response.json();
  if (module === "users") {
    const [cellResponse, sectorResponse] = await Promise.all([apiFetch("locations/cells"), apiFetch("locations/sectors")]);
    const cells = cellResponse.ok ? await cellResponse.json() : [];
    const sectors = sectorResponse.ok ? await sectorResponse.json() : [];
    const cellNames = Object.fromEntries(cells.map((cell) => [cell.id, cell]));
    const sectorNames = Object.fromEntries(sectors.map((sector) => [sector.id, sector.name]));
    return records.map((item) => {
      const cell = cellNames[item.cell_id];
      const location = cell ? `${sectorNames[cell.sector_id] || `Sector #${cell.sector_id}`} / ${cell.name}` : (item.cell_id ? `Cell #${item.cell_id}` : "—");
      return [item.full_name || "Unnamed user", initials(item.full_name || "User"), item.role, item.cooperative_name, location, item.is_active ? "active" : "inactive", item.id];
    });
  }
  if (module === "schemes") return records.map((item) => [item.name, initials(item.name), item.implementing_partner || "-", item.sector_id ? (lookups.sectors[item.sector_id] || `Sector #${item.sector_id}`) : "-", `${item.hectares_developed ? `${item.hectares_developed} ha` : "Area to verify"} · ${item.baseline_yield_target_tons ? `target ${item.baseline_yield_target_tons} t` : "no yield target"}`, item.is_active ? "active" : "reference only", item.id]);
  if (module === "citizen") return records.map((item) => [`${item.crop_type} report`, initials(item.crop_type), item.crop_type, item.pest_or_disease || (item.expected_harvest_tons ? `Forecast ${item.expected_harvest_tons} t` : "Crop update"), schemeName(item.scheme_id), cellName(item.cell_id), item.severity ? (item.severity >= 5 ? "critical" : item.severity >= 4 ? "high" : "triaged") : "active"]);
  if (module === "irrigation") return records.map((item) => [item.infrastructure_name || "Rainfall observation", initials(item.infrastructure_name || "Rain"), schemeName(item.scheme_id), item.operational_status || "reported", item.rainfall_mm === null ? "-" : `${item.rainfall_mm} mm`, item.bottleneck_category || "-", item.operational_status || "active"]);
  if (module === "feedback") return records.map((item) => [`FB-${String(item.id).padStart(3, "0")}`, "FB", item.category, schemeName(item.scheme_id), cellName(item.cell_id), item.assigned_to_user_id ? `User #${item.assigned_to_user_id}` : "Unassigned", item.status]);
  if (module === "accounts") return records.map((item) => [item.full_name, initials(item.full_name || item.email), item.email, item.role, new Date(item.created_at).toLocaleDateString(), item.status, item.id, item.sector_ids || []]);
  if (module === "nutrition") return records.map((item) => [`NS-${String(item.id).padStart(3, "0")}`, "NS", cellName(item.cell_id), item.meals_per_day === 3 ? "3+" : String(item.meals_per_day), item.ate_protein_or_vegetables ? "yes" : "no", item.food_sufficient ? "yes" : "no", item.stunting_risk_score >= 4 ? "high" : item.stunting_risk_score >= 3 ? "medium" : "low"]);
  if (module === "messages") return records.map((item) => [item.phone_number, "SM", item.message, String(item.purpose || "advisory").replaceAll("_", " "), new Date(item.created_at).toLocaleString(), item.status]);
  return records.map((item) => [item.title, initials(item.item_type), item.item_type, schemeName(item.scheme_id), cellName(item.cell_id), new Date(item.created_at).toLocaleDateString(), item.priority]);
}

async function render(module) {
  activeModule = module;
  document.querySelectorAll(".module-link").forEach((button) => button.classList.toggle("active", button.dataset.module === module));
  try { draw(modules[module], liveMode ? await fetchLiveRows(module) : sampleRows(module), liveMode); }
  catch (error) {
    if (error.forbidden) { draw(modules[module], [], true); document.querySelector("#table-body").innerHTML = `<tr><td class="empty-row" colspan="7">${error.message}. Ask an administrator for access.</td></tr>`; return; }
    liveMode = false; document.querySelector("#data-label").textContent = "SAMPLE DATA"; document.querySelector("#data-label").classList.remove("live"); draw(modules[module], sampleRows(module));
  }
}

async function refreshNavigationCounts() {
  const endpoints = { users: "users", schemes: "irrigation-schemes", citizen: "citizen-reports", irrigation: "irrigation-reports", feedback: "feedback", accounts: "auth/accounts", nutrition: "nutrition-surveys", messages: "advisory/messages" };
  await loadLookups();
  await Promise.all(Object.entries(endpoints).map(async ([module, endpoint]) => {
    const badge = document.querySelector(`[data-count="${module}"]`);
    if (!badge) return;
    const response = await apiFetch(endpoint).catch(() => null);
    badge.textContent = response?.ok ? (await response.json()).length.toLocaleString() : "–";
  }));
}

document.querySelectorAll(".module-link").forEach((button) => button.addEventListener("click", () => render(button.dataset.module)));
document.querySelector("#table-search").addEventListener("input", () => { currentPage = 1; updateVisibleRows(); });
document.querySelector("#table-filter").addEventListener("change", () => { currentPage = 1; updateVisibleRows(); });
document.querySelector("#filter-button").addEventListener("click", () => {
  const panel = document.querySelector("#filter-panel");
  panel.hidden = !panel.hidden;
  document.querySelector("#filter-button").setAttribute("aria-expanded", String(!panel.hidden));
});
document.querySelector("#clear-filters").addEventListener("click", () => {
  document.querySelector("#table-search").value = "";
  document.querySelector("#table-filter").value = "all";
  currentPage = 1;
  updateVisibleRows();
});
document.querySelector("#previous-page").addEventListener("click", () => { if (currentPage > 1) { currentPage -= 1; updateVisibleRows(); } });
document.querySelector("#next-page").addEventListener("click", () => { currentPage += 1; updateVisibleRows(); });
document.querySelector("#table-body").addEventListener("click", async (event) => {
  const action = event.target.dataset.action;
  const userId = event.target.dataset.id;
  if (!action || !userId) return;
  if (action === "toggle-account") {
    const next = event.target.dataset.status === "active" ? "suspended" : "active";
    if (next === "suspended" && !confirm("Suspend this account? The person is signed out immediately.")) return;
    const response = await apiFetch(`auth/accounts/${userId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: next }) });
    if (response.ok) { CS.toast(`Account ${next}`, "success"); await render("accounts"); } else alert(`Could not update account: ${response.status}`);
    return;
  }
  if (action === "edit-scheme") { openSchemeEditor(Number(userId)); return; }
  if (action === "account-area") { openAreaDialog(Number(userId), event.target.dataset.sectors ? event.target.dataset.sectors.split(",").map(Number) : []); return; }
  if (action === "delete") {
    if (!confirm("Permanently delete this user? Users linked to reports can only be deactivated.")) return;
    const response = await apiFetch(`users/${userId}`, { method: "DELETE" });
    if (response.status === 204) { await refreshNavigationCounts(); await render("users"); return; }
    if (response.status === 409) {
      if (!confirm("This user has report or case history. Deactivate the account instead?")) return;
      const deactivated = await apiFetch(`users/${userId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: false }) });
      if (deactivated.ok) { await render("users"); return; }
      alert(`Could not deactivate user: ${deactivated.status}`);
      return;
    }
    alert(`Could not delete user: ${response.status}`);
  }
  if (action === "edit") {
    const row = event.target.closest("tr");
    const cells = row.querySelectorAll("td");
    const name = prompt("Full name", row.querySelector("strong").textContent);
    if (name === null) return;
    const cooperative = prompt("Cooperative", cells[2]?.textContent.trim() || "");
    if (cooperative === null) return;
    const cellId = prompt("Cell ID (enter the numeric ID from the cells table)", "");
    if (cellId === null) return;
    const response = await apiFetch(`users/${userId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: name, cooperative_name: cooperative, cell_id: Number(cellId) }) });
    if (response.ok) await render("users"); else alert(`Could not update user: ${response.status}`);
  }
});
async function connectApi() {
  const label = document.querySelector("#data-label");
  const button = document.querySelector("#connect-api");
  if (button.dataset.switchAccount) { await CS.signOut(); return; }
  try {
    const probe = await apiFetch("users");
    if (probe.status === 403) throw new Error("Your role cannot manage platform data");
    if (probe.status === 401) { CS.session.clear(); window.location.href = "login.html?next=management.html"; return; }
    if (!probe.ok) throw new Error(`API returned ${probe.status}`);
    liveMode = true;
    await refreshNavigationCounts();
    await render(activeModule);
    if (!liveMode) throw new Error("Could not load management records");
    label.textContent = "POSTGRESQL CONNECTED";
    label.title = API;
    label.classList.add("live");
    button.textContent = "API connected OK";
  } catch (error) {
    liveMode = false;
    label.title = `${error.message}. Endpoint: ${API}`;
    label.classList.remove("live");
    if (error.message.startsWith("Your role")) {
      // Signed in, but as a Citizen Science Monitor: management is for planners and administrators.
      const role = String(CS.session.account()?.role || "this account").replaceAll("_", " ");
      label.textContent = "PLANNERS & ADMINS ONLY";
      button.textContent = "Sign in as another user";
      button.dataset.switchAccount = "1";
      CS.toast(`You are signed in as ${role}. Platform management needs a District Planner or administrator account.`, "warn");
    } else {
      label.textContent = "API UNAVAILABLE";
      button.textContent = "Reconnect PostgreSQL";
    }
  }
}
document.querySelector("#connect-api").addEventListener("click", connectApi);

// Area-level access: an account limited to some sectors sees cases, grievances, people and reports from those sectors only.
function areaLabel(role, sectorIds) {
  if (role === "administrator" || !sectorIds || !sectorIds.length) return "Whole district";
  return sectorIds.map((id) => lookups.sectors[id] || `Sector #${id}`).join(", ");
}

function openAreaDialog(accountId, current) {
  const areaDialog = document.querySelector("#area-dialog");
  const list = document.querySelector("#area-sectors");
  const sectors = Object.entries(lookups.sectors).sort((a, b) => a[1].localeCompare(b[1]));
  list.innerHTML = sectors.length
    ? sectors.map(([id, name]) => `<label class="area-option"><input type="checkbox" value="${Number(id)}" ${current.includes(Number(id)) ? "checked" : ""}> ${escapeHtml(name)}</label>`).join("")
    : "<p>No sectors are loaded yet. Run scripts/load_locations.py first.</p>";
  areaDialog.dataset.account = accountId;
  document.querySelector("#area-message").textContent = "";
  areaDialog.showModal();
}

document.querySelector("#area-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const areaDialog = document.querySelector("#area-dialog");
  const sectorIds = [...document.querySelectorAll("#area-sectors input:checked")].map((input) => Number(input.value));
  const response = await apiFetch(`auth/accounts/${areaDialog.dataset.account}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sector_ids: sectorIds }) });
  if (!response.ok) { document.querySelector("#area-message").textContent = `Could not save the area (${response.status}).`; return; }
  areaDialog.close();
  CS.toast(sectorIds.length ? "Area saved. The person sees these sectors from their next page load." : "Area cleared: whole district.", "success");
  await render("accounts");
});
["#area-close", "#area-cancel"].forEach((id) => document.querySelector(id)?.addEventListener("click", () => document.querySelector("#area-dialog").close()));
document.querySelector("#area-clear")?.addEventListener("click", () => document.querySelectorAll("#area-sectors input").forEach((input) => { input.checked = false; }));

const dialog = document.querySelector("#user-dialog");
document.querySelector("#table-body").addEventListener("change", async (event) => {
  const select = event.target.closest(".role-select");
  if (!select) return;
  const response = await apiFetch(`auth/accounts/${select.dataset.account}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role: select.value }) });
  if (response.ok) CS.toast(`Role changed to ${select.value.replaceAll("_", " ")}`, "success"); else { alert(`Could not change role: ${response.status}`); await render("accounts"); }
});
const csvCell = (value) => {
  let cell = String(value ?? "");
  if (/^\s*[=+\-@]/.test(cell)) cell = `'${cell}`;
  return `"${cell.replaceAll('"', '""')}"`;
};
document.querySelector("#export-button").addEventListener("click", () => {
  const headers = activeModule === "users" ? [...modules.users.columns, "User ID"] : modules[activeModule].columns;
  const records = renderedRows.flatMap((row, index) => {
    const tableRow = document.querySelectorAll("#table-body tr")[index];
    if (!tableRow || tableRow.hidden) return [];
    return [activeModule === "users" ? [row[0], row[2], row[3], row[4], row[5], row[6]] : [row[0], ...row.slice(2)]];
  });
  const csv = "\uFEFF" + [headers, ...records].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `cs-ircfs-${activeModule}-${renderedLive ? "postgresql" : "demonstration"}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
});
const entryDefinitions = {
  schemes: { title: "Add irrigation scheme", endpoint: "irrigation-schemes", fields: [
    ["name", "Scheme name", "text", true], ["implementing_partner", "Implementing partner", "text"],
    ["hectares_developed", "Developed hectares", "number"], ["baseline_yield_target_tons", "Verified yield target (tons)", "number"],
    ["baseline_source", "Yield target source", "text"], ["sector_id", "Sector", "location-sector"],
    ["latitude", "Latitude", "number"], ["longitude", "Longitude", "number"]
  ] },
  citizen: { title: "Add citizen report", endpoint: "citizen-reports", fields: [
    ["crop_type", "Crop type", "text", true], ["reporter_id", "Reporter", "location-user"],
    ["scheme_id", "Scheme", "location-scheme"], ["sector_id", "Sector", "location-sector", true], ["cell_id", "Cell", "location-cell", true],
    ["planting_date", "Planting date", "date"], ["expected_harvest_tons", "Expected harvest (tons)", "number"],
    ["reported_harvest_tons", "Reported harvest (tons)", "number"], ["pest_or_disease", "Pest or disease", "text"],
    ["severity", "Severity", "severity"], ["notes", "Notes", "textarea"], ["latitude", "Latitude (map point)", "number"], ["longitude", "Longitude (map point)", "number"]
  ] },
  irrigation: { title: "Add rainfall or irrigation report", endpoint: "irrigation-reports", fields: [
    ["reporter_id", "Reporter", "location-user"], ["scheme_id", "Scheme", "location-scheme"], ["sector_id", "Sector", "location-sector", true], ["cell_id", "Cell", "location-cell", true],
    ["infrastructure_name", "Asset or rain gauge name", "text"],
    ["operational_status", "Operational status", "select", false, ["", "operational", "faulty", "offline"]],
    ["bottleneck_category", "Bottleneck category", "select", false, ["", "technical", "social", "institutional", "environmental"]],
    ["rainfall_mm", "Rainfall (mm)", "number"], ["fault_description", "Fault description", "textarea"], ["latitude", "Latitude (map point)", "number"], ["longitude", "Longitude (map point)", "number"]
  ] },
  nutrition: { title: "Add household nutrition survey", endpoint: "nutrition-surveys", fields: [
    ["reporter_id", "Reporter", "location-user"], ["sector_id", "Sector", "location-sector", true], ["cell_id", "Cell", "location-cell", true],
    ["meals_per_day", "Meals eaten yesterday", "select", true, ["", "1", "2", "3"]],
    ["ate_protein_or_vegetables", "Children ate meat, eggs, milk or vegetables this week", "select", true, ["", "yes", "no"]],
    ["food_sufficient", "Enough food until the next harvest", "select", true, ["", "yes", "no"]]
  ] },
  feedback: { title: "Add community feedback", endpoint: "feedback", fields: [
    ["category", "Category", "text", true], ["message", "Message", "textarea", true],
    ["reporter_id", "Reporter (optional for anonymous feedback)", "location-user"],
    ["scheme_id", "Scheme", "location-scheme"], ["sector_id", "Sector", "location-sector", true], ["cell_id", "Cell", "location-cell", true], ["latitude", "Latitude (map point)", "number"], ["longitude", "Longitude (map point)", "number"]
  ] }
};
const entryDialog = document.querySelector("#entry-dialog");
const entryForm = document.querySelector("#entry-form");
document.querySelector("#add-button").addEventListener("click", async () => {
  if (activeModule === "analytics") { window.location.href = `planner.html${window.location.search}#act-now`; return; }
  if (activeModule === "accounts" || activeModule === "messages") { await refreshNavigationCounts(); await render(activeModule); return; }
  if (activeModule === "users") { document.querySelector("#form-message").textContent = ""; await loadUserLocations(); dialog.showModal(); return; }
  const definition = entryDefinitions[activeModule];
  document.querySelector("#entry-title").textContent = definition.title;
  document.querySelector("#entry-message").textContent = "";
  entryForm.reset();
  const container = document.querySelector("#entry-fields");
  container.replaceChildren();
  for (const [name, title, type, required, options] of definition.fields) {
    const label = document.createElement("label");
    label.textContent = title;
    const field = document.createElement(type === "textarea" ? "textarea" : type === "select" ? "select" : "input");
    field.name = name;
    field.required = Boolean(required);
    if (type === "location-cell") {
      field.add(new Option("Choose a registered cell", ""));
    } else if (type === "location-sector") {
      field.add(new Option("Choose a registered sector", ""));
      apiFetch("locations/sectors").then(async (response) => {
        if (response.ok) (await response.json()).forEach((sector) => field.add(new Option(sector.name, sector.id)));
      }).catch(() => {});
    } else if (type === "location-scheme") {
      field.add(new Option("Choose a scheme", ""));
      apiFetch("irrigation-schemes").then(async (response) => {
        if (response.ok) (await response.json()).forEach((scheme) => field.add(new Option(scheme.name, scheme.id)));
      }).catch(() => {});
    } else if (type === "location-user") {
      field.add(new Option("Choose a user", ""));
      apiFetch("users").then(async (response) => {
        if (response.ok) (await response.json()).forEach((user) => field.add(new Option(`${user.full_name || "Unnamed user"} (${user.phone_number || "no phone"})`, user.id)));
      }).catch(() => {});
    } else if (type === "number" || type === "integer" || type === "severity") {
      field.type = "number";
      field.step = type === "number" ? "any" : "1";
      field.min = type === "severity" || type === "integer" ? "1" : name === "latitude" ? "-90" : name === "longitude" ? "-180" : "0";
      if (type === "severity") field.max = "5";
      if (name === "rainfall_mm") field.max = "500";
      if (name === "latitude") field.max = "90";
      if (name === "longitude") field.max = "180";
    } else if (type === "date") field.type = "date";
    else if (type === "text") field.type = "text";
    if (type === "select") options.forEach((option) => field.add(new Option(option || "Select...", option)));
    if (name === "message") field.minLength = 5;
    if (name === "category") field.minLength = 2;
    label.append(field);
    container.append(label);
    if (name === "latitude") {
      const locationButton = document.createElement("button");
      locationButton.type = "button";
      locationButton.className = "secondary-button location-button";
      locationButton.textContent = "Use my current map location";
      locationButton.addEventListener("click", () => {
        if (!navigator.geolocation) { document.querySelector("#entry-message").textContent = "Location is not available in this browser."; return; }
        navigator.geolocation.getCurrentPosition((position) => {
          field.value = position.coords.latitude.toFixed(6);
          const longitude = container.querySelector('[name="longitude"]');
          if (longitude) longitude.value = position.coords.longitude.toFixed(6);
          document.querySelector("#entry-message").textContent = "Location added from your device.";
        }, () => { document.querySelector("#entry-message").textContent = "Location permission was denied or unavailable."; });
      });
      container.append(locationButton);
    }
  }
  const sectorField = container.querySelector('[name="sector_id"]');
  const cellField = container.querySelector('[name="cell_id"]');
  if (sectorField && cellField) {
    try {
      const response = await apiFetch("locations/cells");
      const cells = response.ok ? await response.json() : [];
      const updateCells = () => {
        const selectedSector = Number(sectorField.value);
        cellField.replaceChildren(new Option(selectedSector ? "Choose a cell" : "Choose a sector first", ""));
        cells.filter((cell) => !selectedSector || cell.sector_id === selectedSector).forEach((cell) => cellField.add(new Option(cell.name, cell.id)));
        cellField.disabled = !selectedSector;
      };
      sectorField.addEventListener("change", updateCells);
      updateCells();
    } catch (_) { /* keep the empty cell selector if the API is unavailable */ }
  }
  entryDialog.showModal();
});
document.querySelector("#entry-close").addEventListener("click", () => entryDialog.close());
document.querySelector("#entry-cancel").addEventListener("click", () => entryDialog.close());
entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const definition = entryDefinitions[activeModule];
  const payload = {};
  for (const [name, , type] of definition.fields) {
    const value = new FormData(entryForm).get(name);
    if (value === null || String(value).trim() === "") continue;
    payload[name] = ["number", "integer", "severity", "location-user", "location-scheme", "location-sector", "location-cell"].includes(type) ? Number(value) : String(value).trim();
  }
  delete payload.sector_id;
  if (activeModule === "nutrition") {
    payload.meals_per_day = Number(payload.meals_per_day);
    payload.ate_protein_or_vegetables = payload.ate_protein_or_vegetables === "yes";
    payload.food_sufficient = payload.food_sufficient === "yes";
  }
  const message = document.querySelector("#entry-message");
  if (activeModule === "schemes" && payload.baseline_yield_target_tons !== undefined && !payload.baseline_source) {
    message.textContent = "Enter a source for the verified yield target.";
    return;
  }
  try {
    if (!liveMode) await connectApi();
    if (!liveMode) throw new Error("Connect to PostgreSQL before saving.");
    const response = await apiFetch(definition.endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(Array.isArray(error.detail) ? error.detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join("; ") : error.detail || `Save failed (${response.status})`);
    }
    entryDialog.close();
    await refreshNavigationCounts();
    await render(activeModule);
  } catch (error) { message.textContent = error.message; }
});
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());
async function loadUserLocations() {
  const sectorField = document.querySelector("#user-sector");
  const cellField = document.querySelector("#user-cell");
  if (!sectorField || !liveMode) return;
  const [sectorResponse, cellResponse] = await Promise.all([apiFetch("locations/sectors"), apiFetch("locations/cells")]);
  if (!sectorResponse.ok || !cellResponse.ok) return;
  const sectors = await sectorResponse.json();
  const cells = await cellResponse.json();
  sectorField.replaceChildren(new Option("Choose a sector", ""));
  sectors.forEach((sector) => sectorField.add(new Option(sector.name, sector.id)));
  sectorField.onchange = () => {
    const selected = Number(sectorField.value);
    cellField.replaceChildren(new Option(selected ? "Choose a cell" : "Choose a sector first", ""));
    cellField.disabled = !selected;
    cells.filter((cell) => cell.sector_id === selected).forEach((cell) => cellField.add(new Option(cell.name, cell.id)));
  };
}
document.querySelector("#user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries([...new FormData(event.currentTarget)].filter(([, value]) => String(value).trim() !== ""));
  delete payload.sector_id;
  for (const name of ["cell_id", "latitude", "longitude"]) if (name in payload) payload[name] = Number(payload[name]);
  const message = document.querySelector("#form-message");
  try {
    if (!liveMode) await connectApi();
    if (!liveMode) throw new Error("Connect to PostgreSQL before saving.");
    const result = await apiFetch("users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!result.ok) {
      const error = await result.json();
      throw new Error(Array.isArray(error.detail) ? error.detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join("; ") : error.detail || "Could not save user");
    }
    await refreshNavigationCounts();
    dialog.close();
    event.currentTarget.reset();
    await render("users");
  } catch (error) { message.textContent = error.message; }
});

render("users");
if (CS.session.token() || sessionStorage.getItem("cs_ircfs_api_key")) connectApi().then(loadUserLocations);
else apiFetch("users").then((probe) => { if (probe.ok) connectApi().then(loadUserLocations); }).catch(() => {});
document.querySelector("#connect-api").addEventListener("click", () => window.setTimeout(loadUserLocations, 250));

// Edit verified scheme figures, e.g. the feasibility-study yield target used for outcome verification.
async function openSchemeEditor(schemeId) {
  const response = await apiFetch("irrigation-schemes");
  const scheme = response.ok ? (await response.json()).find((item) => item.id === schemeId) : null;
  if (!scheme) return;
  document.querySelector("#entry-title").textContent = `Edit ${scheme.name}`;
  document.querySelector("#entry-message").textContent = "Only enter figures confirmed in official scheme documents, and record their source.";
  const container = document.querySelector("#entry-fields");
  const fields = [["implementing_partner", "Implementing partner", "text"], ["hectares_developed", "Developed hectares", "number"], ["baseline_yield_target_tons", "Feasibility-study yield target (tons)", "number"], ["baseline_source", "Source of the yield target", "text"], ["is_active", "Status", "select"]];
  container.innerHTML = fields.map(([name, label, type]) => type === "select"
    ? `<label>${label}<select name="${name}"><option value="true" ${scheme.is_active ? "selected" : ""}>Active (pilot scheme)</option><option value="false" ${scheme.is_active ? "" : "selected"}>Reference only</option></select></label>`
    : `<label>${label}<input name="${name}" type="${type}" ${type === "number" ? 'step="any" min="0"' : ""} value="${escapeHtml(scheme[name] ?? "")}" /></label>`).join("");
  entryForm.dataset.editScheme = String(schemeId);
  entryDialog.showModal();
}
// Runs before the generic "add record" handler (capture phase) and takes over when editing a scheme.
entryForm.addEventListener("submit", async (event) => {
  if (!entryForm.dataset.editScheme) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const payload = {};
  for (const [name, value] of new FormData(entryForm).entries()) {
    if (String(value).trim() === "") continue;
    payload[name] = name === "is_active" ? value === "true" : ["hectares_developed", "baseline_yield_target_tons"].includes(name) ? Number(value) : String(value).trim();
  }
  const response = await apiFetch(`irrigation-schemes/${entryForm.dataset.editScheme}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    document.querySelector("#entry-message").textContent = typeof error.detail === "string" ? error.detail : `Save failed (${response.status})`;
    return;
  }
  entryDialog.close();
  CS.toast("Scheme figures saved", "success");
  await refreshNavigationCounts();
  await render("schemes");
}, true);
entryDialog.addEventListener("close", () => { delete entryForm.dataset.editScheme; });

