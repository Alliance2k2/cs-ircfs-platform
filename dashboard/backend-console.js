const API = new URLSearchParams(window.location.search).get("api") || (window.location.port === "8080" ? "http://127.0.0.1:8002/api/v1" : `${window.location.origin}/api/v1`);
const apiFetch = (path) => fetch(`${API}/${path}`, { headers: sessionStorage.getItem("cs_ircfs_api_key") ? { "X-API-Key": sessionStorage.getItem("cs_ircfs_api_key") } : {} });

async function refreshStatus() {
  const statusText = document.querySelector("#api-status-text");
  try {
    const [health, summary, queue] = await Promise.all([
      fetch(new URL("../../health", `${API}/`)).then((r) => r.ok ? r.json() : Promise.reject()),
      apiFetch("analytics/dashboard-summary").then((r) => r.ok ? r.json() : Promise.reject()),
      apiFetch("analytics/act-now").then((r) => r.ok ? r.json() : Promise.reject())
    ]);
    document.querySelector("#status-light").classList.add("online");
    statusText.textContent = "API online";
    document.querySelector("#service-health").textContent = health.status === "ok" ? "Online" : "Check service";
    document.querySelector("#live-reports").textContent = summary.total_reports.toLocaleString();
    document.querySelector("#live-alerts").textContent = queue.length.toLocaleString();
    document.querySelector("#live-feedback").textContent = summary.open_complaints.toLocaleString();
  } catch (_) {
    statusText.textContent = "API unavailable or key required";
    document.querySelector("#service-health").textContent = "Offline";
    document.querySelector("#source-badge").textContent = "START API TO CONNECT";
  }
}

document.querySelector("#refresh").addEventListener("click", refreshStatus);
refreshStatus();
