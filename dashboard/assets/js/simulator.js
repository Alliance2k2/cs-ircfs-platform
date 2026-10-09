// Feature-phone simulator: drives the real USSD and SMS callbacks and shows what each step created.
const { apiFetch, apiJson, escapeHtml, toast } = window.CS;
const $ = (selector) => document.querySelector(selector);
const RECORD_LABEL = { crop_report: "Crop report", irrigation_report: "Water / infrastructure report", community_feedback: "Anonymous grievance", nutrition_survey: "Nutrition survey", location: "Caller location" };
const RECORD_LINK = { crop_report: "act-now.html", irrigation_report: "advice.html", community_feedback: "feedback.html", nutrition_survey: "nutrition.html" };

let channel = "ussd";
let sessionId = null;
let steps = [];
let traceStarted = false;

const caller = () => $("#caller-input").value.trim() || $("#caller-select").value;

function tickClock() {
  $("#phone-clock").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function loadCallers() {
  try {
    const users = await apiJson("field-users");
    const select = $("#caller-select");
    const priority = { citizen_science_monitor: 0, cooperative_leader: 1, farmer: 2 };
    const callers = users.filter((user) => user.is_active).sort((a, b) => (priority[a.role] ?? 9) - (priority[b.role] ?? 9) || Number(!a.cell_id) - Number(!b.cell_id));
    const options = callers.slice(0, 60).map((user) => new Option(`${user.full_name || "Unnamed"} · ${user.phone_number}${user.role !== "farmer" ? ` (${user.role.replaceAll("_", " ")})` : ""}`, user.phone_number));
    if (options.length) select.replaceChildren(...options, new Option("+250 788 000 001 (new farmer)", "+250788000001"));
  } catch (_) { /* without sign-in the list stays generic; any number can still dial */ }
}

/* ---------- Trace and English box ---------- */
function addTrace({ kind, sent, reply, english, recordType, recordId }) {
  const trace = $("#trace");
  if (!traceStarted) { trace.innerHTML = ""; traceStarted = true; }
  const item = document.createElement("li");
  item.className = `trace-item ${kind}`;
  item.innerHTML = `<div class="trace-line"><span class="trace-badge">${kind === "ussd" ? "USSD" : "SMS"}</span><code>${escapeHtml(sent)}</code><span class="trace-time">${new Date().toLocaleTimeString()}</span></div>
    <p class="trace-reply">${escapeHtml(reply)}</p>${english ? `<p class="trace-en">${escapeHtml(english)}</p>` : ""}
    ${recordType ? `<a class="trace-record" href="${RECORD_LINK[recordType] || "planner.html"}">✓ Saved: ${escapeHtml(RECORD_LABEL[recordType] || recordType)} #${recordId} → view on dashboard</a>` : ""}`;
  trace.prepend(item);
  if (recordType) toast(`Saved to the database: ${RECORD_LABEL[recordType] || recordType} #${recordId}`, "success");
}

function showEnglish(text) {
  const box = $("#english-box");
  box.hidden = !$("#show-english").checked || !text;
  box.textContent = text ? `English: ${text.replace(/^(CON|END) /, "")}` : "";
}

/* ---------- USSD ---------- */
async function ussdRequest() {
  const text = steps.join("*");
  const response = await apiFetch("simulator/ussd", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sessionId, serviceCode: "*801#", phoneNumber: caller(), text }) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `The USSD service answered ${response.status}`);
  return data;
}

function renderUssd(data) {
  const ended = data.response.startsWith("END ");
  $("#ussd-text").textContent = data.response.replace(/^(CON|END) /, "");
  $("#ussd-form").hidden = ended;
  $("#ussd-ok").hidden = !ended;
  showEnglish(data.english);
  if (!ended) { $("#ussd-input").value = ""; $("#ussd-input").focus(); } else { $("#ussd-ok").focus(); }
}

async function dial() {
  sessionId = `sim-${Date.now().toString(36)}`;
  steps = [];
  $("#ussd-idle").hidden = true;
  $("#ussd-session").hidden = false;
  $("#ussd-text").textContent = "USSD code running…";
  $("#ussd-form").hidden = true;
  $("#ussd-ok").hidden = true;
  try {
    const data = await ussdRequest();
    addTrace({ kind: "ussd", sent: "*801#", reply: data.response, english: data.english });
    renderUssd(data);
  } catch (error) {
    $("#ussd-text").textContent = `Connection problem.\n${error.message}\n\nIs the platform running?`;
    $("#ussd-ok").hidden = false;
  }
}

async function sendUssd(answer) {
  steps.push(answer.trim());
  $("#ussd-text").textContent = "Sending…";
  try {
    const data = await ussdRequest();
    addTrace({ kind: "ussd", sent: steps.join("*"), reply: data.response, english: data.english, recordType: data.record_type, recordId: data.record_id });
    renderUssd(data);
    if (data.record_type) loadActivity();
  } catch (error) {
    $("#ussd-text").textContent = `Connection problem.\n${error.message}`;
    $("#ussd-form").hidden = true;
    $("#ussd-ok").hidden = false;
  }
}

function hangUp() {
  sessionId = null;
  steps = [];
  $("#ussd-session").hidden = true;
  $("#ussd-idle").hidden = false;
  showEnglish("");
}

/* ---------- SMS ---------- */
function bubble(text, side) {
  const thread = $("#sms-thread");
  const item = document.createElement("div");
  item.className = `bubble ${side}`;
  item.textContent = text;
  thread.append(item);
  thread.scrollTop = thread.scrollHeight;
}

async function sendSms(text) {
  if (!text.trim()) return;
  bubble(text, "out");
  $("#sms-input").value = "";
  try {
    const response = await apiFetch("simulator/sms", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: caller(), to: "8448", text }) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `The SMS service answered ${response.status}`);
    window.setTimeout(() => bubble(data.reply, "in"), 450);
    addTrace({ kind: "sms", sent: text, reply: data.reply, recordType: data.record_type, recordId: data.record_id });
    if (data.record_type) loadActivity();
  } catch (error) {
    bubble(`Not delivered: ${error.message}`, "in error");
  }
}

/* ---------- Live activity ---------- */
async function loadActivity() {
  const list = $("#activity");
  try {
    const activity = await apiJson("channels/activity?limit=12");
    const items = [
      ...activity.inbound.map((m) => ({ ...m, label: m.channel === "ussd" ? "USSD" : "SMS in" })),
      ...activity.outbound.map((m) => ({ ...m, label: "SMS out", text: m.message })),
      ...activity.rewards.map((r) => ({ ...r, label: "Airtime", text: `${r.amount_rwf} RWF · ${r.reason} (${r.status.replace("_", " ")})` }))
    ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 12);
    list.innerHTML = items.length ? items.map((m) => `<li><span class="activity-tag ${escapeHtml(m.label.replace(" ", "-").toLowerCase())}">${escapeHtml(m.label)}</span><span class="activity-phone">${escapeHtml(m.phone_number)}</span><code>${escapeHtml(m.text || "")}</code>${m.record_type ? `<em>→ ${escapeHtml(RECORD_LABEL[m.record_type] || m.record_type)} #${m.record_id}</em>` : m.purpose ? `<em>${escapeHtml(m.purpose.replaceAll("_", " "))}</em>` : ""}</li>`).join("")
      : '<li class="trace-empty">No field activity yet.</li>';
  } catch (error) {
    list.innerHTML = `<li class="trace-empty">${error.status === 401 || error.status === 403 ? 'Sign in as a monitor, officer or planner to see everyone\'s activity. <a href="login.html">Sign in</a>' : "Start the platform to see live activity."}</li>`;
  }
}

/* ---------- Events ---------- */
function selectChannel(next) {
  channel = next;
  $("#tab-ussd").setAttribute("aria-selected", String(next === "ussd"));
  $("#tab-sms").setAttribute("aria-selected", String(next === "sms"));
  $("#panel-ussd").hidden = next !== "ussd";
  $("#panel-sms").hidden = next !== "sms";
  $("#sms-shortcuts").hidden = next !== "sms";
  $("#english-box").hidden = next !== "ussd" || !$("#show-english").checked || !$("#english-box").textContent;
  (next === "sms" ? $("#sms-input") : $("#dial-button")).focus();
}

$("#tab-ussd").addEventListener("click", () => selectChannel("ussd"));
$("#tab-sms").addEventListener("click", () => selectChannel("sms"));
$("#dial-button").addEventListener("click", dial);
$("#ussd-form").addEventListener("submit", (event) => { event.preventDefault(); const value = $("#ussd-input").value; if (value.trim()) sendUssd(value); });
$("#ussd-cancel").addEventListener("click", hangUp);
$("#ussd-ok").addEventListener("click", hangUp);
$("#sms-form").addEventListener("submit", (event) => { event.preventDefault(); sendSms($("#sms-input").value); });
document.querySelectorAll("[data-sms]").forEach((button) => button.addEventListener("click", () => sendSms(button.dataset.sms)));
$("#show-english").addEventListener("change", () => { $("#english-box").hidden = !$("#show-english").checked || !$("#english-box").textContent; });
$("#clear-trace").addEventListener("click", () => { traceStarted = false; $("#trace").innerHTML = '<li class="trace-empty">Cleared. Dial *801# or send an SMS.</li>'; });
document.querySelectorAll("[data-key]").forEach((button) => button.addEventListener("click", () => {
  const key = button.dataset.key;
  const target = channel === "sms" ? $("#sms-input") : !$("#ussd-session").hidden && !$("#ussd-form").hidden ? $("#ussd-input") : null;
  if (!target) {
    if (channel === "ussd" && $("#ussd-session").hidden && key === "#") dial();
    return;
  }
  target.value = key === "back" ? target.value.slice(0, -1) : target.value + key;
  target.focus();
}));

tickClock();
window.setInterval(tickClock, 30000);
loadCallers();
loadActivity();
window.setInterval(() => { if (!document.hidden) loadActivity(); }, 8000);
