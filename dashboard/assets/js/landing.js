// Public landing page: template behaviour (menu, reveal, counters, FAQ, EN/RW menu) plus live platform data.
(() => {
  const { API, escapeHtml, session } = window.CS;
  const $ = (selector) => document.querySelector(selector);
  const fmt = (n) => Number(n || 0).toLocaleString();

  // ---------- Header: mobile menu, active section, language ----------
  const menuBtn = $("#menuBtn");
  const links = $("#site-links");
  const closeMenu = () => { links.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); menuBtn.setAttribute("aria-label", "Open navigation"); };
  menuBtn.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", String(open));
    menuBtn.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  });
  links.querySelectorAll("a").forEach((a) => a.addEventListener("click", closeMenu));

  const NAV = {
    en: { label: "EN", items: ["Our mission", "Live map", "Solutions", "How it works", "Pilot projects", "FAQs"] },
    rw: { label: "RW", items: ["Intego yacu", "Ikarita", "Ibisubizo", "Uko bikora", "Imishinga y'igerageza", "Ibibazo"] },
  };
  let lang = "en";
  $("#langBtn").addEventListener("click", () => {
    lang = lang === "en" ? "rw" : "en";
    $("#langLabel").textContent = NAV[lang].label;
    links.querySelectorAll("a[data-nav]").forEach((a, i) => { a.textContent = NAV[lang].items[i]; });
    $("#langBtn").title = lang === "rw" ? "Menu in Kinyarwanda; page text is in English" : "English menu";
  });

  if ("IntersectionObserver" in window) {
    const navLinks = [...links.querySelectorAll("a[data-nav]")];
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${entry.target.id}`));
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    navLinks.forEach((a) => { const target = document.querySelector(a.getAttribute("href")); if (target) spy.observe(target); });
  }

  // ---------- Signed-in people go straight to the dashboard ----------
  if (session.account()) {
    $("#nav-cta").innerHTML = 'Open dashboard <i class="bi bi-arrow-up-right" aria-hidden="true"></i>';
    $("#hero-cta").innerHTML = 'Open live dashboard <i class="bi bi-arrow-up-right" aria-hidden="true"></i>';
    $("#cta-main").innerHTML = 'Open dashboard <i class="bi bi-arrow-up-right" aria-hidden="true"></i>';
    ["#nav-cta", "#hero-cta", "#cta-main", "#mobile-cta", "#preview-cta"].forEach((id) => { const link = $(id); if (link) link.href = "planner.html"; });
    const mobile = $("#mobile-cta"); if (mobile) mobile.textContent = "Open dashboard";
  }

  $("#year").textContent = new Date().getFullYear();

  // ---------- Scroll: progress bar, compact header, back-to-top ----------
  const progress = $("#scroll-progress"), header = $("#header"), toTop = $("#to-top");
  let ticking = false;
  function onScroll() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const y = window.scrollY;
    progress.style.transform = `scaleX(${max > 0 ? Math.min(1, y / max) : 0})`;
    header.classList.toggle("scrolled", y > 40);
    toTop.classList.toggle("show", y > 900);
    ticking = false;
  }
  window.addEventListener("scroll", () => { if (!ticking) { ticking = true; window.requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  // ---------- Reveal on scroll and project-fact counters ----------
  const revealItems = document.querySelectorAll(".reveal");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if ("IntersectionObserver" in window && !reduceMotion) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visible"); observer.unobserve(e.target); } });
    }, { threshold: 0.12 });
    revealItems.forEach((el) => observer.observe(el));
  } else {
    revealItems.forEach((el) => el.classList.add("visible"));
  }

  // Only fixed project facts from the proposal are animated here, never live figures.
  function animateCount(el) {
    const end = Number(el.dataset.count), suffix = el.dataset.suffix || "";
    if (reduceMotion) { el.textContent = end + suffix; return; }
    const begin = performance.now(), duration = 1200;
    function frame(now) {
      const t = Math.min((now - begin) / duration, 1), ease = 1 - Math.pow(1 - t, 3);
      el.textContent = (Number.isInteger(end) ? Math.round(end * ease) : (end * ease).toFixed(1)) + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  if ("IntersectionObserver" in window) {
    const counters = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { animateCount(e.target); counters.unobserve(e.target); } });
    }, { threshold: 0.7 });
    document.querySelectorAll("[data-count]").forEach((el) => counters.observe(el));
  }

  // Keep one FAQ answer open at a time.
  const faqs = document.querySelectorAll(".faq-list details");
  faqs.forEach((d) => d.addEventListener("toggle", () => { if (d.open) faqs.forEach((other) => { if (other !== d) other.open = false; }); }));

  // ---------- Live map of sectors ----------
  function ago(value) {
    const seconds = Math.max(0, (Date.now() - new Date(String(value).endsWith("Z") || String(value).includes("+") ? value : `${value}Z`)) / 1000);
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
    return `${Math.floor(seconds / 86400)} d ago`;
  }

  const LEVEL = { irrigate_more: ["#d9822b", "Dry: irrigate more", 0], reduce: ["#3d8bb0", "Wet: irrigate less", 1], normal: ["#2f9e6e", "Normal", 2], no_data: ["#a9b5b0", "No rain data", 3] };
  const HOME_VIEW = [[-2.22, 30.15], 10];
  let map = null, sectorLayer = null, districtBounds = null;
  function showDistrict() {
    if (!map) return;
    if (districtBounds) map.fitBounds(districtBounds, { padding: [16, 16] });
    else map.setView(...HOME_VIEW);
  }
  function ensureMap() {
    if (map || !window.L) return;
    map = L.map("public-map", { scrollWheelZoom: false }).setView(...HOME_VIEW);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 18, className: "soft-tiles" }).addTo(map);
    sectorLayer = L.layerGroup().addTo(map);
    fetch("assets/data/bugesera-boundary.geojson").then((r) => r.json()).then((geo) => {
      const outline = L.geoJSON(geo, { style: { color: "#167949", weight: 2, fillColor: "#167949", fillOpacity: 0.05 }, interactive: false }).addTo(map);
      districtBounds = outline.getBounds();
      showDistrict();
    }).catch(() => {});
  }
  $("#map-reset").addEventListener("click", showDistrict);

  function renderSectors(sectors) {
    ensureMap();
    if (sectorLayer) {
      sectorLayer.clearLayers();
      sectors.filter((s) => s.latitude && s.longitude).forEach((s) => {
        const [color, label] = LEVEL[s.advice_level] || LEVEL.no_data;
        const rain = (s.rainfall_mm_7d == null ? "no rain-gauge readings yet" : `${s.rainfall_mm_7d} mm rain in 7 days`)
          + (s.forecast_mm_7d == null ? "" : `<br>Forecast: ${s.forecast_mm_7d} mm in the next 7 days`);
        L.circleMarker([s.latitude, s.longitude], { radius: 7 + Math.sqrt(s.reports_30d) * 4, color: "#fff", weight: 2, fillColor: color, fillOpacity: 0.85 })
          .bindTooltip(`<b>${escapeHtml(s.name)}</b><br>${s.reports_30d} report${s.reports_30d === 1 ? "" : "s"} in 30 days<br>${escapeHtml(label)} · ${rain}`, { className: "sector-tip", direction: "top" })
          .addTo(sectorLayer);
      });
    }
    const withData = sectors.filter((s) => s.advice_level !== "no_data").sort((a, b) => (LEVEL[a.advice_level]?.[2] ?? 9) - (LEVEL[b.advice_level]?.[2] ?? 9));
    const missing = sectors.length - withData.length;
    const forecasts = sectors.filter((s) => s.advice_level === "no_data" && s.forecast_mm_7d != null).map((s) => s.forecast_mm_7d);
    const range = forecasts.length ? ` Forecast: ${Math.round(Math.min(...forecasts))}–${Math.round(Math.max(...forecasts))} mm of rain in the next 7 days.` : "";
    $("#advice").innerHTML = (withData.length
      ? withData.map((s) => `<li><i class="lvl-${escapeHtml(s.advice_level)}"></i><b>${escapeHtml(s.name)} · ${s.rainfall_mm_7d} mm</b><span>${escapeHtml(s.advice_en)}</span></li>`).join("")
      : `<li class="more">No rain-gauge readings this week yet. Monitors report rain with *801# option 3, or by SMS: IMVURA 12.${range}</li>`)
      + (missing && withData.length ? `<li class="more">${missing} more sector${missing === 1 ? "" : "s"} without rain data this week.${range}</li>` : "");
  }

  async function refresh() {
    const dot = $("#live-dot"), time = $("#live-time");
    try {
      const response = await fetch(`${API}/public/overview`);
      if (!response.ok) throw new Error(response.status);
      const data = await response.json();
      const values = { reports: fmt(data.reports), field_messages: fmt(data.field_messages), farmers: fmt(data.farmers),
                       monitors: fmt(data.monitors), schemes: fmt(data.active_schemes),
                       sectors: `${data.sectors_reporting}${data.sectors_total ? ` / ${data.sectors_total}` : ""}` };
      document.querySelectorAll("[data-stat]").forEach((el) => { el.textContent = values[el.dataset.stat]; });
      $("#feed").innerHTML = data.recent.length
        ? data.recent.slice(0, 5).map((item) => `<li><i class="${escapeHtml(item.kind)}"></i><span>${escapeHtml(item.label)}${item.sector ? ` <em>· ${escapeHtml(item.sector)}</em>` : ""}</span><small>${ago(item.created_at)}</small></li>`).join("")
        : `<li><span class="empty">The pilot is starting. Reports appear here live as soon as farmers dial *801# or text 8448.</span></li>`;
      const forecasts = (data.sectors || []).map((s) => s.forecast_mm_7d).filter((v) => v !== null && v !== undefined);
      $("#forecast").hidden = !forecasts.length;
      if (forecasts.length) {
        const low = Math.round(Math.min(...forecasts)), high = Math.round(Math.max(...forecasts));
        $("#forecast-range").textContent = low === high ? `${low} mm across Bugesera` : `${low}–${high} mm across Bugesera`;
      }
      renderSectors(data.sectors || []);
      renderPreview(data);
      tickerItems = data.recent.slice(0, 8).map((item) => `${item.label}${item.sector ? ` · ${item.sector}` : ""} · ${ago(item.created_at)}`);
      setFooterStatus(true, `Platform online · ${fmt(data.reports)} reports from the field`);
      dot.classList.remove("off");
      document.querySelectorAll("[data-live-badge]").forEach((badge) => { badge.textContent = "LIVE"; badge.classList.remove("off"); });
      time.textContent = `updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } catch (_) {
      dot.classList.add("off");
      document.querySelectorAll("[data-live-badge]").forEach((badge) => { badge.textContent = "OFFLINE"; badge.classList.add("off"); });
      time.textContent = "offline";
      $("#feed").innerHTML = `<li><span class="empty">Live figures appear when the platform is running.</span></li>`;
      $("#sector-bars").innerHTML = `<p class="preview-empty">Sector activity appears when the platform is running.</p>`;
      $("#preview-feed").innerHTML = `<li class="preview-empty">No connection to the platform.</li>`;
      setFooterStatus(false, "Platform offline · live figures paused");
      ensureMap();
    }
  }

  // ---------- Live platform preview ----------
  const KIND_ICON = { pest: "bug", fault: "tools", rain: "cloud-rain", harvest: "basket", water: "droplet", feedback: "chat-left-text", nutrition: "heart-pulse" };
  function renderPreview(data) {
    const sectors = [...(data.sectors || [])].filter((s) => s.reports_30d > 0).sort((a, b) => b.reports_30d - a.reports_30d).slice(0, 6);
    const top = Math.max(1, ...sectors.map((s) => s.reports_30d));
    $("#sector-bars").innerHTML = sectors.length
      ? sectors.map((s, i) => `<div class="sector-bar ${s.advice_level === "irrigate_more" ? "dry" : s.advice_level === "reduce" ? "wet" : ""}"><span>${escapeHtml(s.name)}</span><div class="track"><i style="width:${Math.max(3, (s.reports_30d / top) * 100)}%;animation-delay:${i * 80}ms"></i></div><b>${s.reports_30d}</b></div>`).join("")
      : `<p class="preview-empty">No sector has reported in the last 30 days yet.</p>`;
    $("#preview-feed").innerHTML = data.recent.length
      ? data.recent.slice(0, 4).map((item) => `<li class="${escapeHtml(item.kind)}"><i class="bi bi-${KIND_ICON[item.kind] || "clipboard-data"}" aria-hidden="true"></i><div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.sector || "Bugesera")} · ${ago(item.created_at)}</small></div></li>`).join("")
      : `<li class="preview-empty">Reports appear here as soon as farmers dial *801#.</li>`;
  }

  function setFooterStatus(online, text) {
    const status = document.querySelector("[data-footer-status]");
    if (!status) return;
    status.classList.toggle("online", online);
    status.classList.toggle("offline", !online);
    status.querySelector("span").textContent = text;
  }

  // ---------- Top-strip ticker: cycles the latest public report summaries ----------
  let tickerItems = [], tickerIndex = 0;
  const tickerText = $("#ticker-text");
  window.setInterval(() => {
    if (document.hidden || !tickerItems.length) return;
    tickerText.classList.add("swap");
    window.setTimeout(() => {
      tickerText.textContent = tickerItems[tickerIndex % tickerItems.length];
      tickerIndex += 1;
      tickerText.classList.remove("swap");
    }, 350);
  }, 4500);

  // ---------- Phone demo: the real *801# screens for a pest report ----------
  const SCREENS = [
    { text: "*801#", key: "#", caption: "Dial *801#", dial: true },
    { text: "Kaze kuri CS-IRCFS. Hitamo:\n1. Rapora umusaruro\n2. Indwara/udukoko\n3. Rapora imvura\n4. Ibikorwa remezo byo kuhira\n5. Tanga ikibazo/igitekerezo\n6. Imirire y'urugo", key: "2", caption: "Main menu · press 2 for pests & disease" },
    { text: "Igihingwa cyafashwe:\n1. Umuceri\n2. Ibigori\n3. Ibishyimbo\n4. Imyumbati\n5. Imboga", key: "2", caption: "Which crop? 2 = maize" },
    { text: "Hitamo ikibazo:\n1. Nzana\n2. Indwara y'ibibabi\n3. Indwara y'imizi\n4. Ibindi byonnyi", key: "1", caption: "Which problem? 1 = fall armyworm" },
    { text: "Ubukana bw'ikibazo:\n1. Buke\n2. Buringaniye\n3. Bukabije\n4. Bukabije cyane\n5. Byangiritse byose", key: "5", caption: "How severe? 5 = everything damaged" },
    { text: "Murakoze! Raporo #1 ya Nzana yakiriwe.\nAbashinzwe ubuhinzi bamenyeshejwe.", key: null, caption: "Saved. Planners see a critical case straight away." },
  ];
  let step = 0;
  const ussd = $("#ussd"), caption = $("#ussd-caption"), keys = [...document.querySelectorAll("#keys span")];
  function showScreen() {
    const screen = SCREENS[step];
    ussd.classList.add("is-fading");
    window.setTimeout(() => {
      ussd.textContent = screen.text;
      ussd.classList.toggle("dial", Boolean(screen.dial));
      caption.textContent = screen.caption;
      ussd.classList.remove("is-fading");
    }, 250);
    if (screen.key) {
      const key = keys.find((k) => k.textContent === screen.key);
      window.setTimeout(() => { key?.classList.add("press"); window.setTimeout(() => key?.classList.remove("press"), 350); }, 2300);
    }
    step = (step + 1) % SCREENS.length;
  }
  showScreen();
  window.setInterval(() => { if (!document.hidden) showScreen(); }, 2900);

  refresh();
  window.setInterval(() => { if (!document.hidden) refresh(); }, 20000);
})();
