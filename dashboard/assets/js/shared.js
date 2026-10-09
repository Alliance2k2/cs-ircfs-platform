// Shared helpers for every CS-IRCFS page: API access, sign-in session, language, notices.
(function () {
  const params = new URLSearchParams(window.location.search);
  const API = params.get("api") || (window.location.port === "8080" ? "http://127.0.0.1:8002/api/v1" : `${window.location.origin}/api/v1`);
  const KEYS = { session: "cs_ircfs_session", account: "cs_ircfs_account", apiKey: "cs_ircfs_api_key", apiUrl: "cs_ircfs_api_url", lang: "cs_ircfs_lang" };

  const store = {
    get(area, key) { try { return window[area].getItem(key); } catch (_) { return null; } },
    set(area, key, value) { try { window[area].setItem(key, value); } catch (_) { /* storage blocked: keep working without it */ } },
    remove(area, key) { try { window[area].removeItem(key); } catch (_) { /* ignore */ } }
  };
  store.set("sessionStorage", KEYS.apiUrl, API);

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  function authHeaders() {
    const token = store.get("sessionStorage", KEYS.session);
    if (token) return { Authorization: `Bearer ${token}` };
    const key = store.get("sessionStorage", KEYS.apiKey);
    return key ? { "X-API-Key": key } : {};
  }

  const apiFetch = (path, options = {}) => fetch(`${API}/${path}`, { ...options, headers: { ...(options.headers || {}), ...authHeaders() } });

  async function apiJson(path, options = {}) {
    const init = { ...options };
    if (init.body && typeof init.body !== "string") {
      init.body = JSON.stringify(init.body);
      init.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
    }
    const response = await apiFetch(path, init);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((item) => `${item.loc?.at(-1)}: ${item.msg}`).join("; ") : data.detail;
      const error = new Error(detail || `Request failed (${response.status})`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  const session = {
    token: () => store.get("sessionStorage", KEYS.session),
    account() { try { return JSON.parse(store.get("sessionStorage", KEYS.account) || "null"); } catch (_) { return null; } },
    start(result) {
      store.set("sessionStorage", KEYS.session, result.access_token);
      store.set("sessionStorage", KEYS.account, JSON.stringify(result.account));
    },
    clear() { store.remove("sessionStorage", KEYS.session); store.remove("sessionStorage", KEYS.account); },
    setApiKey(key) { store.set("sessionStorage", KEYS.apiKey, key); },
    clearApiKey() { store.remove("sessionStorage", KEYS.apiKey); }
  };

  async function signOut() {
    await apiFetch("auth/logout", { method: "POST" }).catch(() => null);
    session.clear();
    window.location.href = "login.html";
  }

  // English / Kinyarwanda. Kinyarwanda strings should be reviewed by the field team before the pilot.
  const STRINGS = {
    "nav.home": ["Home", "Ahabanza"], "nav.overview": ["Overview", "Incamake"], "nav.actnow": ["Act now", "Ibyihutirwa"],
    "nav.channels": ["Field channels", "Ubutumwa bwo mu murima"], "nav.schemes": ["Scheme performance", "Imikorere y'imishinga"],
    "nav.advice": ["Irrigation advice", "Inama zo kuhira"], "nav.food": ["Household nutrition", "Imirire y'ingo"],
    "nav.map": ["Map & observations", "Ikarita n'ibyagaragaye"], "nav.feedback": ["Community feedback", "Ibitekerezo by'abaturage"],
    "nav.simulator": ["Phone simulator", "Igerageza rya telefoni"], "nav.management": ["Platform management", "Gucunga urubuga"],
    "nav.dashboard": ["Planner dashboard", "Imbonerahamwe y'igenamigambi"], "nav.console": ["Technical console", "Ibya tekiniki"],
    "data.source": ["Data source", "Inkomoko y'amakuru"], "data.demo": ["DEMONSTRATION DATA", "AMAKURU Y'IGERAGEZA"],
    "data.live": ["LIVE DATABASE", "AMAKURU NYAYO"], "data.connect": ["Connect live data", "Huza n'amakuru nyayo"],
    "greet.morning": ["Good morning", "Mwaramutse"], "greet.afternoon": ["Good afternoon", "Mwiriwe"], "greet.evening": ["Good evening", "Mwiriwe"],
    "greet.planner": ["Planner", "Mugenamigambi"],
    "top.subtitle": ["A clear view of irrigation performance, crop risks, and community action.", "Ishusho isobanutse y'imikorere yo kuhira, ibyago ku bihingwa n'ibikorwa by'abaturage."],
    "top.scheme": ["Scheme", "Umushinga"], "top.allSchemes": ["All schemes", "Imishinga yose"],
    "metric.farmers": ["Registered farmers", "Abahinzi banditswe"], "metric.reports": ["Total reports", "Raporo zose"],
    "metric.schemes": ["Active schemes", "Imishinga ikora"], "metric.complaints": ["Open complaints", "Ibibazo bitarakemuka"],
    "metric.households": ["Households surveyed", "Ingo zabajijwe"], "metric.rewards": ["Airtime rewards", "Ibihembo by'itumanaho"],
    "metric.reportsNote": ["USSD, SMS and web", "USSD, SMS n'urubuga"], "metric.schemesNote": ["PADAB & APEFA Solar", "PADAB na APEFA Solar"],
    "actnow.eyebrow": ["PRIORITISED WORK QUEUE", "IBIKORWA BIKURIKIRANYE"], "actnow.title": ["Act now", "Ibikeneye gukorwa vuba"],
    "actnow.sub": ["Reports needing district attention, ranked by urgency.", "Raporo zikeneye ubufasha bw'akarere, zikurikiranye uko byihutirwa."],
    "filter.all": ["All", "Byose"], "filter.infrastructure": ["Infrastructure", "Ibikorwa remezo"], "filter.pests": ["Pests & disease", "Udukoko n'indwara"],
    "filter.feedback": ["Feedback", "Ibitekerezo"], "btn.refresh": ["Refresh", "Vugurura"], "btn.open": ["Open case", "Fungura"],
    "channels.eyebrow": ["NO INTERNET NEEDED", "NTA MURANDASI UKENEWE"], "channels.title": ["Field channels, live", "Ubutumwa buva mu murima"],
    "channels.sub": ["Feature-phone reports arrive through USSD and SMS, are stored centrally, and appear here.", "Raporo za telefoni zisanzwe zinyura kuri USSD na SMS, zikabikwa hamwe, zikagaragara hano."],
    "channels.open": ["Open phone simulator", "Fungura igerageza rya telefoni"], "channels.empty": ["No field messages yet. Dial *801# in the simulator.", "Nta butumwa buraza. Kanda *801# mu igerageza."],
    "perf.eyebrow": ["OUTCOME VERIFICATION · OBJECTIVES 1-2", "ISUZUMA RY'IBYAGEZWEHO"], "perf.title": ["Scheme performance", "Imikorere y'imishinga"],
    "perf.sub": ["Farmer-reported harvest against each scheme's yield target, with recurring bottlenecks flagged automatically.", "Umusaruro wavuzwe n'abahinzi ugereranyijwe n'intego ya buri mushinga."],
    "health.eyebrow": ["COMMUNITY ACCOUNTABILITY", "KUBAZWA INSHINGANO"], "health.title": ["Response health", "Uko ibibazo bisubizwa"],
    "advice.eyebrow": ["IRRIGATION SCHEDULING ASSISTANT", "UMUFASHA MU KUHIRA"], "advice.title": ["Irrigation advice by sector", "Inama zo kuhira ku murenge"],
    "advice.sub": ["Seven-day rain-gauge totals become SMS advice for cooperatives.", "Imvura y'iminsi 7 ihinduka inama zoherezwa kuri SMS."],
    "advice.send": ["Send advice to cooperatives", "Ohereza inama ku makoperative"],
    "food.eyebrow": ["HOUSEHOLD NUTRITION TRACKER", "IMIRIRE Y'INGO"], "food.title": ["Food security & stunting risk", "Kwihaza mu biribwa n'igwingira"],
    "map.eyebrow": ["SPATIAL INTELLIGENCE", "AMAKURU KU IKARITA"], "map.title": ["Map & live observations", "Ikarita n'ibyagaragaye"],
    "map.reset": ["Reset Bugesera view", "Garura Bugesera yose"],
    "layer.schemes": ["Schemes", "Imishinga"], "layer.infrastructure": ["Infrastructure", "Ibikorwa remezo"], "layer.crops": ["Crop reports", "Raporo z'ibihingwa"],
    "layer.heat": ["Pest heatmap", "Ikarita y'udukoko"], "layer.rain": ["Rainfall & drought", "Imvura n'amapfa"], "layer.food": ["Nutrition risk", "Ibyago by'imirire"],
    "layer.farmers": ["Farmers", "Abahinzi"],
    "signin": ["Sign in", "Injira"], "signout": ["Sign out", "Sohoka"], "lang": ["Language", "Ururimi"],
    "case.save": ["Save", "Bika"], "case.cancel": ["Close", "Funga"], "case.notify": ["Notify the community by SMS", "Menyesha abaturage kuri SMS"],
    "sim.title": ["Field phone simulator", "Igerageza rya telefoni"],
  };
  const LANGS = ["en", "rw"];
  let lang = store.get("localStorage", KEYS.lang) === "rw" ? "rw" : "en";
  const t = (key, fallback) => (STRINGS[key] ? STRINGS[key][LANGS.indexOf(lang)] : fallback ?? key);

  function applyI18n(root = document) {
    document.documentElement.lang = lang === "rw" ? "rw" : "en";
    root.querySelectorAll("[data-i18n]").forEach((element) => { element.textContent = t(element.dataset.i18n, element.textContent); });
    root.querySelectorAll("[data-i18n-title]").forEach((element) => { element.title = t(element.dataset.i18nTitle, element.title); });
    root.querySelectorAll(".lang-toggle button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.lang === lang)));
  }

  function setLang(next) {
    lang = LANGS.includes(next) ? next : "en";
    store.set("localStorage", KEYS.lang, lang);
    applyI18n();
    document.dispatchEvent(new CustomEvent("cs:lang", { detail: lang }));
  }

  function toast(message, kind = "info") {
    let host = document.querySelector(".toast-host");
    if (!host) { host = document.createElement("div"); host.className = "toast-host"; host.setAttribute("aria-live", "polite"); document.body.append(host); }
    const item = document.createElement("div");
    item.className = `toast ${kind}`;
    item.textContent = message;
    host.append(item);
    window.setTimeout(() => item.classList.add("leaving"), 4200);
    window.setTimeout(() => item.remove(), 4700);
  }

  // Language switch and signed-in user menu, placed into any element with [data-header-controls].
  function mountHeaderControls() {
    document.querySelectorAll("[data-header-controls]").forEach((host) => {
      const account = session.account();
      const initials = account ? (account.full_name || account.email).split(/\s+/).map((word) => word[0]).join("").slice(0, 2).toUpperCase() : "";
      host.innerHTML = `<div class="lang-toggle" role="group" aria-label="${escapeHtml(t("lang"))}"><button type="button" data-lang="en">EN</button><button type="button" data-lang="rw">RW</button></div>`
        + (account
          ? `<div class="user-chip"><span class="user-avatar">${escapeHtml(initials)}</span><span class="user-meta"><strong>${escapeHtml(account.full_name || account.email)}</strong><small>${escapeHtml(String(account.role).replaceAll("_", " "))}</small></span><button type="button" class="user-signout" data-i18n="signout">Sign out</button></div>`
          : `<a class="user-signin" href="login.html" data-i18n="signin">Sign in</a>`);
      host.querySelectorAll(".lang-toggle button").forEach((button) => button.addEventListener("click", () => setLang(button.dataset.lang)));
      host.querySelector(".user-signout")?.addEventListener("click", signOut);
    });
    applyI18n();
  }

  // Keep ?api=… when moving between pages.
  function preserveApiParam() {
    if (!params.has("api")) return;
    document.querySelectorAll("a[href$='.html'], a[href*='.html#']").forEach((link) => {
      const url = new URL(link.getAttribute("href"), window.location.href);
      url.searchParams.set("api", params.get("api"));
      link.href = url.pathname.split("/").pop() + url.search + url.hash;
    });
  }

  window.CS = { API, apiFetch, apiJson, escapeHtml, session, signOut, t, get lang() { return lang; }, setLang, applyI18n, toast, mountHeaderControls };
  document.addEventListener("DOMContentLoaded", () => { mountHeaderControls(); preserveApiParam(); });
})();
