// One shell for every signed-in page: sidebar, top bar and footer, built from a single navigation list.
// Load after shared.js and before the page script, because page scripts bind to elements created here
// (#data-mode, #load-live-data, #nav-alert-count on the planner; .module-link, #data-label, #connect-api in management).
(() => {
  const { escapeHtml, session } = window.CS;
  const page = document.body.dataset.page || "overview";
  // Dashboard pages share the planner script (app.js) and its data-source status block.
  const DASHBOARD_PAGES = ["overview", "act-now", "channels", "schemes", "trends", "advice", "food", "map", "feedback", "cooperatives"];
  const onDashboard = DASHBOARD_PAGES.includes(page);

  const GROUPS = [
    { label: "Dashboard", items: [
      { href: "/app/", icon: "stars", label: "Executive overview (new)", page: "executive" },
      { href: "planner.html", icon: "speedometer2", label: "Overview", i18n: "nav.overview", page: "overview" },
      { href: "act-now.html", icon: "exclamation-triangle", label: "Act now", i18n: "nav.actnow", page: "act-now", badge: onDashboard ? "nav-alert-count" : null, plannerOnly: true },
      { href: "channels.html", icon: "phone-vibrate", label: "Field channels", i18n: "nav.channels", page: "channels" },
      { href: "schemes.html", icon: "bar-chart-line", label: "Scheme performance", i18n: "nav.schemes", page: "schemes" },
      { href: "trends.html", icon: "graph-up-arrow", label: "Trends", page: "trends" },
    ] },
    { label: "Field intelligence", items: [
      { href: "advice.html", icon: "cloud-rain", label: "Irrigation advice", i18n: "nav.advice", page: "advice" },
      { href: "nutrition.html", icon: "heart-pulse", label: "Household nutrition", i18n: "nav.food", page: "food" },
      { href: "map.html", icon: "geo-alt", label: "Map & observations", i18n: "nav.map", page: "map" },
      { href: "feedback.html", icon: "chat-left-text", label: "Community feedback", i18n: "nav.feedback", page: "feedback" },
      { href: "cooperatives.html", icon: "people", label: "Cooperatives", page: "cooperatives" },
    ] },
    { label: "Platform", items: [
      { href: "management.html", icon: "gear", label: "Platform management", i18n: "nav.management", page: "management", plannerOnly: true },
      { href: "report.html", icon: "file-earmark-bar-graph", label: "Monthly report", page: "report" },
      { href: "simulator.html", icon: "telephone", label: "Phone simulator", i18n: "nav.simulator", page: "simulator" },
      { href: "backend-console.html", icon: "terminal", label: "Technical console", i18n: "nav.console", page: "console" },
    ] },
  ];

  // Platform Management modules appear under their page link while on that page.
  const MODULES = [
    ["users", "people", "Users"], ["cooperatives", "people", "Cooperatives"], ["schemes", "droplet-half", "Irrigation schemes"], ["citizen", "clipboard-data", "Citizen reports"],
    ["irrigation", "cloud-rain", "Rainfall & irrigation"],    ["feedback", "chat-left-text", "Community feedback"],
    ["categories", "list-ul", "Grievance categories"], ["assets", "tools", "Scheme assets"],
    ["nutrition", "heart-pulse", "Household nutrition"],
    ["messages", "chat-dots", "SMS log"], ["accounts", "person-badge", "Accounts"], ["analytics", "graph-up-arrow", "Analytics", false],
  ];

  const CRUMBS = { overview: ["Dashboard", "Overview"], "act-now": ["Dashboard", "Act now"], channels: ["Dashboard", "Field channels"],
                   schemes: ["Dashboard", "Scheme performance"], trends: ["Dashboard", "Trends"], advice: ["Field intelligence", "Irrigation advice"],
                   food: ["Field intelligence", "Household nutrition"], map: ["Field intelligence", "Map & observations"],                   feedback: ["Field intelligence", "Community feedback"], cooperatives: ["Field intelligence", "Cooperatives"],
                   management: ["Platform management", "Users"], report: ["Reports", "Monthly field report"],
                   simulator: ["Field channels", "Phone simulator"], console: ["Platform", "Technical console"] };

  // Status block in the sidebar: the planner and management scripts drive these elements.
  const STATUS = {
    dashboard: `<p class="app-status-label" data-i18n="data.source">Data source</p>
      <span id="data-mode" class="mode-pill">CONNECTING…</span>
      <button id="load-live-data" class="text-button" type="button">Reconnect</button>
      <p id="live-pulse" class="live-pulse" hidden><i></i> Auto-refresh every 15 s</p>`,
    management: `<p class="app-status-label">Current view</p>
      <span id="data-label" class="data-label">CONNECTING…</span>
      <button id="connect-api" class="connect-button" type="button">Connect local API</button>`,
  };

  const navItem = (item) => {
    const current = item.page === page;
    const label = item.i18n ? `<em data-i18n="${item.i18n}">${escapeHtml(item.label)}</em>` : `<em>${escapeHtml(item.label)}</em>`;
    const badge = item.badge ? `<b id="${item.badge}" class="app-badge">0</b>` : "";
    return `<a class="nav-link${current ? " active" : ""}" href="${item.href}"${current ? ' aria-current="page"' : ""}${item.plannerOnly && onDashboard ? " data-planner-only" : ""} title="${escapeHtml(item.label)}"><span class="app-nav-icon bi bi-${item.icon}" aria-hidden="true"></span>${label}${badge}</a>`;
  };

  const moduleItems = () => `<div class="app-subnav" role="group" aria-label="Management modules">${MODULES.map(([key, icon, label, counted = true], index) =>
    `<button type="button" class="nav-link module-link${index === 0 ? " active" : ""}" data-module="${key}" title="${escapeHtml(label)}"><span class="app-nav-icon bi bi-${icon}" aria-hidden="true"></span><em>${escapeHtml(label)}</em>${counted ? `<b data-count="${key}">-</b>` : ""}</button>`).join("")}</div>`;

  const account = session.account();
  const initials = account ? (account.full_name || account.email).split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase() : "";
  const userCard = account
    ? `<div class="app-user"><span class="app-user-avatar">${escapeHtml(initials)}</span><span class="app-user-meta"><strong>${escapeHtml(account.full_name || account.email)}</strong><small>${escapeHtml(String(account.role).replaceAll("_", " "))}</small></span><span class="app-online" title="Signed in"></span></div>`
    : `<a class="app-user app-user-guest" href="login.html?next=${encodeURIComponent(location.pathname.split("/").pop() || "planner.html")}"><span class="app-user-avatar"><i class="bi bi-person" aria-hidden="true"></i></span><span class="app-user-meta"><strong>Not signed in</strong><small>Sign in for live data</small></span><i class="bi bi-box-arrow-in-right" aria-hidden="true"></i></a>`;

  // ---------- Sidebar ----------
  const sidebar = document.querySelector("[data-app-sidebar]");
  if (sidebar) {
    sidebar.innerHTML = `
      <div class="app-brand-row">
        <a class="app-brand" href="index.html" title="CS-IRCFS public site">
          <img src="assets/img/logo-96.png" alt="" width="46" height="46">
          <span><strong>CS-IRCFS</strong><small>Bugesera · resilience platform</small></span>
        </a>
        <button class="app-collapse-btn" type="button" data-sidebar-collapse aria-label="Collapse sidebar" title="Collapse sidebar"><i class="bi bi-chevron-double-left" aria-hidden="true"></i></button>
      </div>
      <nav class="app-nav" aria-label="Main navigation">
        ${GROUPS.map((group) => `<p class="app-nav-label"><span>${group.label}</span></p>${group.items.map((item) => navItem(item) + (item.page === "management" && page === "management" ? moduleItems() : "")).join("")}`).join("")}
        <p class="app-nav-label"><span>Public</span></p>
        <a class="nav-link nav-external" href="index.html" title="Home"><span class="app-nav-icon bi bi-house-door" aria-hidden="true"></span><em data-i18n="nav.home">Home</em></a>
      </nav>
      <a class="app-channel-card" href="simulator.html">
        <span class="bi bi-broadcast-pin" aria-hidden="true"></span>
        <span><strong>USSD *801# · SMS 8448</strong><small>Farmers report from any phone</small></span>
      </a>
      ${STATUS[onDashboard ? "dashboard" : page] ? `<div class="app-status">${STATUS[onDashboard ? "dashboard" : page]}</div>` : ""}
      ${userCard}`;
  }

  // ---------- Top bar ----------
  const [section, current] = CRUMBS[page] || CRUMBS.overview;
  const destinations = [...GROUPS.flatMap((g) => g.items), { href: "index.html", label: "Public home page" }, { href: "login.html", label: "Sign in" },
    ...(page === "management" ? MODULES.map(([key, , label]) => ({ href: `#module-${key}`, label: `Management: ${label}`, module: key })) : [])];
  const topbar = document.querySelector("[data-app-topbar]");
  if (topbar) {
    const today = new Date().toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
    topbar.innerHTML = `
      <div class="app-topbar-left">
        <button class="app-icon-btn app-menu-btn" type="button" data-sidebar-toggle aria-label="Open menu" aria-expanded="false"><i class="bi bi-list" aria-hidden="true"></i></button>
        <div class="app-crumb"><span>CS-IRCFS</span><i class="bi bi-chevron-right" aria-hidden="true"></i><span>${escapeHtml(section)}</span><i class="bi bi-chevron-right" aria-hidden="true"></i><strong id="crumb">${escapeHtml(current)}</strong></div>
      </div>
      <form class="app-search" role="search" data-app-search>
        <i class="bi bi-search" aria-hidden="true"></i>
        <input type="search" list="app-destinations" placeholder="Jump to a section…" aria-label="Jump to a section" autocomplete="off">
        <kbd>Ctrl K</kbd>
        <datalist id="app-destinations">${destinations.map((d) => `<option value="${escapeHtml(d.label)}"></option>`).join("")}</datalist>
      </form>
      <div class="app-topbar-right">
        <span class="app-date"><i class="bi bi-calendar3" aria-hidden="true"></i>${escapeHtml(today)}</span>
        <span class="app-api" data-api-status title="Platform API"><i></i><span>Checking…</span></span>
        <a class="app-icon-btn app-bell" href="act-now.html" aria-label="Act Now queue" title="Act Now queue"><i class="bi bi-bell" aria-hidden="true"></i><b id="bell-count" hidden>0</b></a>
        <div class="header-controls" data-header-controls></div>
      </div>`;

    topbar.querySelector("[data-app-search]").addEventListener("submit", (event) => {
      event.preventDefault();
      const input = event.currentTarget.querySelector("input");
      const query = input.value.trim().toLowerCase();
      const match = destinations.find((d) => d.label.toLowerCase() === query) || destinations.find((d) => d.label.toLowerCase().includes(query));
      if (!match || !query) return;
      input.value = "";
      if (match.module) document.querySelector(`.module-link[data-module="${match.module}"]`)?.click();
      else window.location.href = match.href;
    });
    topbar.querySelector("[data-app-search] input").addEventListener("change", (event) => event.currentTarget.form.requestSubmit());
    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); topbar.querySelector("[data-app-search] input").focus(); }
    });
  }

  // ---------- Footer ----------
  const footer = document.querySelector("[data-app-footer]");
  if (footer) {
    footer.innerHTML = `
      <div class="app-footer-brand">
        <img src="assets/img/logo-96.png" alt="" width="34" height="34">
        <span><strong>CS-IRCFS · Bugesera District</strong><small>Citizen Science for Irrigation Resilience and Climate-smart Food Security</small></span>
      </div>
      <nav class="app-footer-links" aria-label="Footer">
        <a href="index.html">Public site</a><a href="report.html">Monthly report</a><a href="simulator.html">Phone simulator</a><a href="/docs" target="_blank" rel="noopener">API docs</a>
      </nav>
      <div class="app-footer-meta">
        <span data-api-status><i></i><span>Checking platform…</span></span>
        <small>© ${new Date().getFullYear()} AIMS Rwanda — KTT Office · Counts, not personal data, leave district staff screens.</small>
      </div>`;
  }

  // ---------- Sidebar behaviour: mobile drawer and desktop collapse ----------
  const backdrop = document.querySelector("[data-app-backdrop]");
  const toggle = document.querySelector("[data-sidebar-toggle]");
  function setDrawer(open) {
    if (!sidebar) return;
    sidebar.classList.toggle("show", open);
    if (backdrop) backdrop.hidden = !open;
    toggle?.setAttribute("aria-expanded", String(open));
  }
  toggle?.addEventListener("click", () => setDrawer(!sidebar.classList.contains("show")));
  backdrop?.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") setDrawer(false); });
  sidebar?.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", () => setDrawer(false)));

  const COLLAPSE_KEY = "cs_ircfs_sidebar_collapsed";
  const collapseBtn = document.querySelector("[data-sidebar-collapse]");
  function setCollapsed(collapsed) {
    document.documentElement.classList.toggle("sidebar-collapsed", collapsed);
    collapseBtn?.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    collapseBtn?.setAttribute("title", collapsed ? "Expand sidebar" : "Collapse sidebar");
  }
  try { setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1"); } catch (_) { /* storage blocked */ }
  collapseBtn?.addEventListener("click", () => {
    const next = !document.documentElement.classList.contains("sidebar-collapsed");
    setCollapsed(next);
    try { localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0"); } catch (_) { /* storage blocked */ }
    window.dispatchEvent(new Event("resize"));  // let charts and the map re-measure
  });

  // ---------- Breadcrumb follows the page title or the active section ----------
  const crumb = document.querySelector("#crumb");
  function updateCrumb() {
    const title = document.querySelector("#page-title");
    const active = sidebar?.querySelector(".nav-link.active em");
    const text = title?.textContent.trim() || "";
    if (crumb && text) crumb.textContent = text;
  }
  const watched = [sidebar, document.querySelector("#page-title")].filter(Boolean);
  const crumbObserver = new MutationObserver(updateCrumb);
  watched.forEach((node) => crumbObserver.observe(node, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["class"] }));

  // ---------- Live mirrors: [data-mirror="#id"] copies another element's text ----------
  document.querySelectorAll("[data-mirror]").forEach((target) => {
    const source = document.querySelector(target.dataset.mirror);
    if (!source) return;
    const sync = () => { target.textContent = source.textContent.trim() || "–"; };
    new MutationObserver(sync).observe(source, { childList: true, characterData: true, subtree: true });
    sync();
  });

  // ---------- Act Now bell ----------
  const bell = document.querySelector("#bell-count");
  const showBell = (count) => { if (!bell) return; bell.textContent = count > 99 ? "99+" : String(count); bell.hidden = !count; };
  const sourceCount = document.querySelector("#nav-alert-count");
  if (sourceCount) {
    const sync = () => showBell(Number.parseInt(sourceCount.textContent, 10) || 0);
    new MutationObserver(sync).observe(sourceCount, { childList: true, characterData: true, subtree: true });
    sync();
  } else if (account) {
    window.CS.apiJson("analytics/act-now").then((items) => showBell(Array.isArray(items) ? items.length : (items.items || []).length)).catch(() => {});
  }

  // ---------- Platform status (top bar and footer) ----------
  const healthUrl = `${window.CS.API.replace(/\/api\/v1\/?$/, "")}/health`;
  async function checkHealth() {
    let online = false;
    try { online = (await fetch(healthUrl, { cache: "no-store" })).ok; } catch (_) { online = false; }
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    document.querySelectorAll("[data-api-status]").forEach((node) => {
      node.classList.toggle("online", online);
      node.classList.toggle("offline", !online);
      node.querySelector("span").textContent = node.closest(".app-footer") ? (online ? `Platform online · checked ${time}` : "Platform offline") : (online ? "API online" : "API offline");
    });
  }
  checkHealth();
  window.setInterval(() => { if (!document.hidden) checkHealth(); }, 60000);
})();
