// Public landing page: template behaviour (menu, reveal, FAQ, EN/RW menu) plus live platform data in the hero.
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
    en: { label: "EN", items: ["Our mission", "Solutions", "How it works", "Pilot projects", "FAQs"] },
    rw: { label: "RW", items: ["Intego yacu", "Ibisubizo", "Uko bikora", "Imishinga y'igerageza", "Ibibazo"] },
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
    $("#hero-cta").innerHTML = 'Open dashboard <i class="bi bi-arrow-up-right" aria-hidden="true"></i>';
    ["#nav-cta", "#hero-cta", "#mobile-cta"].forEach((id) => { const link = $(id); if (link) link.href = "/app/"; });
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

  // ---------- Reveal on scroll ----------
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

  // Keep one FAQ answer open at a time.
  const faqs = document.querySelectorAll(".faq-list details");
  faqs.forEach((d) => d.addEventListener("toggle", () => { if (d.open) faqs.forEach((other) => { if (other !== d) other.open = false; }); }));

  // ---------- Live figures in the hero ----------
  function ago(value) {
    const seconds = Math.max(0, (Date.now() - new Date(String(value).endsWith("Z") || String(value).includes("+") ? value : `${value}Z`)) / 1000);
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
    return `${Math.floor(seconds / 86400)} d ago`;
  }

  const KIND_ICON = { pest: "bug", fault: "tools", rain: "cloud-rain", harvest: "basket", water: "droplet", feedback: "chat-left-text", nutrition: "heart-pulse" };
  function setLive(online) {
    $("#hf-dot").classList.toggle("off", !online);
    document.querySelectorAll("[data-live-badge]").forEach((badge) => { badge.textContent = online ? "LIVE" : "OFFLINE"; badge.classList.toggle("off", !online); });
  }

  function renderHero(data) {
    // Before the first report, invite one instead of showing "0 farmer reports".
    $("#hero-reports").textContent = data.reports ? `${fmt(data.reports)} farmer report${data.reports === 1 ? "" : "s"}` : "Pilot starting";
    $("#hero-reports-note").textContent = data.reports ? "Community voices matter" : "Be the first: dial *801#";
    $("#hero-feed").innerHTML = data.recent.length
      ? data.recent.slice(0, 3).map((item) => `<li class="${escapeHtml(item.kind)}"><i class="bi bi-${KIND_ICON[item.kind] || "clipboard-data"}" aria-hidden="true"></i><div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.sector || "Bugesera")} · ${ago(item.created_at)}</small></div></li>`).join("")
      : `<li class="hf-empty">The pilot is starting. Reports appear here as soon as farmers dial *801# or text 8448.</li>`;
    const share = data.sectors_total ? (data.sectors_reporting / data.sectors_total) * 100 : 0;
    $("#sector-progress").style.width = `${Math.max(data.sectors_reporting ? 4 : 0, share)}%`;
  }

  async function refresh() {
    try {
      const response = await fetch(`${API}/public/overview`);
      if (!response.ok) throw new Error(response.status);
      const data = await response.json();
      document.querySelectorAll('[data-stat="sectors"]').forEach((el) => { el.textContent = `${data.sectors_reporting}${data.sectors_total ? ` / ${data.sectors_total}` : ""}`; });
      renderHero(data);
      tickerItems = data.recent.slice(0, 8).map((item) => `${item.label}${item.sector ? ` · ${item.sector}` : ""} · ${ago(item.created_at)}`);
      setFooterStatus(true, `Platform online · ${fmt(data.reports)} reports from the field`);
      setLive(true);
      $("#hf-time").textContent = `updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } catch (_) {
      setLive(false);
      $("#hf-time").textContent = "offline";
      $("#hero-feed").innerHTML = `<li class="hf-empty">Live reports appear here when the platform is running.</li>`;
      setFooterStatus(false, "Platform offline · live figures paused");
    }
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
