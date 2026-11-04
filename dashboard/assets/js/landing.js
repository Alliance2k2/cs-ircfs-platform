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
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && links.classList.contains("open")) { closeMenu(); menuBtn.focus(); } });

  const NAV = {
    en: { label: "EN", items: ["What it does", "How it works", "Who it's for", "Pilot schemes", "FAQs"] },
    rw: { label: "RW", items: ["Ibyo ikora", "Uko ikora", "Abagenewe", "Imishinga y'igerageza", "Ibibazo"] },
  };
  const RW_COPY = {
    "COMMUNITY KNOWLEDGE. SHARED RESILIENCE.":"UBUMENYI BW'ABATURAGE. UBUDAHERANWA.",
    "Connecting Farmers' Knowledge":"Guhuza ubumenyi bw'abahinzi",
    "with Better Irrigation Decisions.":"n'ibyemezo byiza byo kuhira.",
    "CS-IRCFS connects farmers, climate observations and district teams to support irrigation resilience and climate-smart food security in Bugesera, Rwanda.":"CS-IRCFS ihuza abahinzi, amakuru y'ikirere n'abakozi b'akarere kugira ngo ifashe kuhira no guteza imbere umutekano w'ibiribwa mu Karere ka Bugesera.",
    "What it does":"Ibyo ikora", "How it works":"Uko ikora", "Who it's for":"Abagenewe", "Pilot schemes":"Imishinga y'igerageza", "FAQs":"Ibibazo", "Sign in":"Injira", "Create account":"Fungura konti",
    "Transforming agriculture":"Guhindura ubuhinzi", "through community knowledge.":"bishingiye ku bumenyi bw'abaturage.",
    "Empowering farmers in Bugesera District, Rwanda with accessible technology to report, monitor, and improve irrigation resilience for climate-smart food security.":"Duha abahinzi bo mu Karere ka Bugesera, u Rwanda, ikoranabuhanga ryoroshye ryo gutanga amakuru, kugenzura no guteza imbere ubudahangarwa bw'ubuhinzi buhungabanya ikirere.",
    "Citizen Science for Irrigation Resilience":"Ubumenyi bw'abaturage mu kurwanya ubukene bw'amazi", "Try phone reporting":"Gerageza gutanga raporo kuri telefoni", "See How It Works":"Reba uko bikora",
    "No internet":"Nta murongo wa interineti", "Live from the field":"Amakuru avuye mu murima", "connecting…":"birimo guhuzwa…", "offline":"birahari?",
    "District-wide pilot":"Igerageza ku karere hose", "2 pilot schemes":"Imishinga 2 y'igerageza", "Any Phone":"Telefoni iyo ari yo yose", "USSD & SMS Access":"Kubona hakoreshejwe USSD na SMS", "Real-Time":"Mu gihe nyacyo", "Field Evidence":"Ibimenyetso byo mu murima",
    "WHAT IT DOES":"IBYO IKORA", "Three kinds of evidence":"Ubwoko butatu bw'ibimenyetso", "one clear picture.":"igikora ishusho imwe isobanutse.",
    "Farmers know their land. Their reports on crops, water and community concerns show district teams where help is needed first.":"Abahinzi bazi ubutaka bwabo. Raporo zabo ku bihingwa, amazi n'ibibazo by'abaturage zerekana inzego z'akarere aho ubufasha bukenewe mbere.",
    "Citizen science":"Ubumenyi bw'abaturage", "Listen to the land.":"Umva icyo ubutaka kivuga.", "Harvests, pest alerts and household food screening.":"Ibisarurwa, amakuru ku tunyangingo ndetse n'isuzuma ryo mu rugo.", "Pest alerts on a map":"Amakuru ku tunyangingo ku ikarita", "Nutrition risk by cell":"Ingaruka ku mirire ku kagari",
    "Water resilience":"Kudahangarira ikibazo cy'amazi", "Every drop, put to better use.":"Amazi yose akoreshwa neza.", "Pump and canal faults, rain gauges and irrigation advice.":"Ibibazo by'amashanyarazi, imiyoboro, ibipimo by'imvura n'inama zo kuhira.", "Pump and canal health":"Imiterere ya pompe n'imiyoboro", "Weekly advice by SMS":"Inama buri cyumweru kuri SMS",
    "Community voice":"Ijwi ry'abaturage", "Every voice is heard.":"Ijwi rya buri muntu ryumvikana.", "Anonymous concerns, followed up until they are solved.":"Ibibazo byatanzwe mu ibanga, bikurikiranwa kugeza bikemuye.", "No name or number kept":"Nta izina cyangwa nimero ibikwa", "An SMS when it is solved":"SMS igihe ikibazo kimaze gukemuka",
    "HOW IT WORKS":"UKO BIKORA", "Simple for farmers.":"Byoroshye ku bahinzi.", "Powerful for planners.":"Bifitiye imbaraga abayitegura ingamba.", "No smartphone needed":"Nta smartphone ikenewe", "Any feature phone":"Telefoni isanzwe iyo ari yo yose", "Kinyarwanda":"Ikinyarwanda", "Numbered choices":"Amahitamo afite nimero", "Pause demo":"Hagarika urugero", "Play demo":"Komeza urugero",
    "Three steps, from a farmer's phone to a district decision and back.":"Intambwe eshatu, kuva kuri telefoni y'umuhinzi kugeza ku cyemezo cy'akarere, hanyuma bikagaruka.",
    "Step 01":"Intambwe ya 01", "Step 02":"Intambwe ya 02", "Step 03":"Intambwe ya 03", "Farmers report":"Abahinzi batanga amakuru", "Dial *801# or text 8448, in Kinyarwanda, from any phone.":"Kanda *801# cyangwa ohereza ubutumwa kuri 8448 mu Kinyarwanda, ukoresheje telefoni iyo ari yo yose.", "The district sees it":"Ukarere kibona amakuru", "Each report is placed by sector and scheme. Severe pests and broken pumps open a case at once.":"Raporo buri imwe igashyirwa mu murenge no mu mugambi. Tunyangingo dukaze na pompe zangiritse bihita biza ku rwego rwihuse.", "The community hears back":"Abaturage babona igisubizo", "Irrigation advice, airtime, and an SMS saying what was done.":"Inama zo kuhira, amasaha yo guhamagara, na SMS ibwira icyakozwe.",
    "ACCOUNTABILITY":"KUBAZA BITABO", "A report becomes":"Raporo ihinduka", "a verified action.":"igikorwa cyagenzuwe.", "Clear stages help the district respond consistently and tell the community what changed.":"Intambwe zisobanutse zifasha akarere gusubiza mu buryo buhamye kandi zikamenyesha abaturage ibyahindutse.",
    "Citizen reports":"Raporo z'abaturage", "A farmer dials USSD or sends SMS.":"Umuhinzi akanda USSD cyangwa agohereza SMS.", "Evidence is checked":"Ibimenyetso biragenzurwa", "Reading quality and report context are validated.":"Ubwiza bw'amakuru n'aho yavugiye biragenzurwa.", "A case is assigned":"Dosiye ihabwa abayizimiyemo", "Authorized staff set priority and ownership.":"Abakozi bemerewe gushyira ku isonga kandi bagaha ubuyobozi.", "Action is resolved":"Igikorwa kirangiye", "The result is recorded and reviewed.":"Igisubizo kirandikwa kandi kigasuzumwa.", "Community is informed":"Abaturage baramenyeshwa", "The district can send a closing-the-loop SMS.":"Akarere gashobora kohereza SMS igaragaza igisubizo.",
    "WHO IT'S FOR":"ABAGENEWE", "Choose how":"Hitamo uburyo", "you take part.":"uzagiramo uruhare.", "Each group sees what it needs, and nothing more.":"Buri tsinda ribona ibikeneye gusa, nta kindi.",
    "Farmers & cooperatives":"Abahinzi n'amakoperative", "Report from any phone":"Tanga raporo kuri telefoni iyo ari yo yose", "No account and no internet needed.":"Nta konti cyangwa interineti bikenewe.", "Get irrigation advice and airtime back":"Bona inama zo kuhira no kwishyurirwa amaherere",
    "Citizen Science Monitors":"Abagenzuzi b'ubumenyi bw'abaturage", "Follow the live picture":"Kurikirana iby'impamo", "Live field reports and maps":"Raporo zo mu murima n'ikarita", "Rainfall, advice and nutrition by sector":"Imvura, inama n'imirire ku murenge", "New accounts are approved by the district.":"Konti nshya zemezwa n'akarere.",
    "District Planners":"Abategura ingamba z'akarere", "Verify and act":"Emeza kandi ukore", "Assign and resolve cases":"Tanga dosiye kandi ukemure ikibazo", "Send advice and tell each cell what was done":"Ohereza inama kandi ubwire buri kagari ibyakozwe", "The district administrator gives the planner role.":"Umuyobozi w'akarere ni we utanga uruhare rwo gutegura.",
    "PILOT SCHEMES":"IMISHINGA Y'IGERAGEZA", "Starting with two":"Twatangiriye ku mishinga ibiri", "irrigation investments.":"y'ibikorwa byo kuhira.", "Both in Bugesera District. The platform checks what changed for the farmers they serve.":"Zombi ziherereye mu Karere ka Bugesera. Iyi platform igenzura impinduka ku bahinzi zikorerwa.",
    "PADAB · MWESA VALLEY":"PADAB · IKIBAYA CYA MWESA", "Building on existing irrigation infrastructure.":"Twubakiye ku bikorwa biriho byo kuhira.", "Assessing irrigation outcomes and bottlenecks across a scheme with pumping stations and a large canal network.":"Gusuzuma umusaruro n'ingorane byo kuhira mu mushinga ufite pompe n'umuyoboro munini.", "Field evidence":"Ibimenyetso byo mu murima", "Pump monitoring":"Gukurikirana pompe", "Rainfall checks":"Gusuzuma imvura",
    "APEFA · NGERUKA & MAREBA":"APEFA · NGERUKA NA MAREBA", "Making solar-powered irrigation more resilient.":"Guteza imbere imirimo yo kuhira ikoresha izuba.", "Connecting farmer feedback and local observations with the operational performance of solar-powered irrigation.":"Guhuza ibitekerezo by'abahinzi n'ibikorwa byo mu karere n'imikorere y'ibikoresho byo kuhira bikoresha izuba.", "Solar irrigation":"Kuhira hakoreshejwe izuba", "Ngeruka":"Ngeruka", "Mareba":"Mareba",
    "GOOD QUESTIONS":"IBIBAZO BYIZA", "Curious about":"Wifuza kumenya", "how it works?":"uko bikora?", "Short answers about reporting and privacy.":"Ibisubizo bigufi ku gutanga amakuru n'ibanga.",
    "What is CS-IRCFS?":"CS-IRCFS ni iki?", "Citizen Science for Irrigation Resilience and Climate-smart Food Security: farmers' phone reports help Bugesera District check and improve its irrigation schemes.":"Ubumenyi bw'abaturage mu kurwanya ubukene bw'amazi no gushakira umutekano mu biribwa bihanganye n'ihindagurika ry'ikirere: raporo z'abahinzi zifasha Akarere ka Bugesera kugenzura no guteza imbere imishinga yo kuhira.",
    "Do I need a smartphone or internet?":"Ese nkeneye telefone yubugeni cyangwa interineti?", "No. Any phone works: dial *801# or text 8448. The menus are in Kinyarwanda with numbered choices.":"Oya. Telefoni iyo ari yo yose irakora: kanda *801# cyangwa ohereza ubutumwa kuri 8448. Imyanya iri mu Kinyarwanda kandi ifite amahitamo afite nimero.",
    "What do I get back?":"Nzabona iki?", "Irrigation advice for your sector by SMS. Airtime rewards may be available after approved milestones and provider activation; district limits, eligibility and reward status can change.":"Inama zo kuhira muri telefoni y'egerejwe URI muri SMS. Igihembo cya airtime gishobora kuboneka nyuma yo gukora intambwe yemejwe n'ikigo; imipaka y'akarere, inshingano n'igihembo bishobora guhinduka.",
    "Who can see my information?":"Ni nde ushobora kubona amakuru yanjye?", "Authorized district staff can handle reports and personal data under assigned roles. Grievances are stored without a reporter account or phone number. Public pages show only aggregated counts and sector summaries.":"Abakozi b'akarere bemerewe bashobora gukurikirana raporo n'amakuru y'umuntu ku rwego rwabo. Ibibazo bikekwa ntabwo bihuzwa na konti cyangwa nimero ya telefoni. Urubuga rusange rwerekana imibare ihuriweho n'umubare ku murenge gusa.",
    "What happens after I report a problem?":"Haba iki nyuma yo gutanga ikibazo?", "Severe pests and broken pumps reach the district at once. When the problem is solved, everyone in your cell gets an SMS saying what was done.":"Tunyangingo dukomeye na pompe zangiritse bihita bivugwa ku karere. Igihe ikibazo kimaze gukemuka, abaturage bose bo mu kagari basangizwa SMS ibabwira icyo bakoze.",
    "Turning community knowledge into better decisions for irrigation resilience and food security.":"Guhindura ubumenyi bw'abaturage mu mfatiro zo gufata ibyemezo byiza byo kurwanya ubukene bw'amazi no guhimiriza umutekano w'ibiribwa.", "Bugesera District, Rwanda":"Akarere ka Bugesera, u Rwanda", "English & Kinyarwanda":"Icyongereza n'Ikinyarwanda", "Public counts and sector summaries only.":"Imibare rusange n'incamake y'imirenge gusa.", "Checking the platform…":"Reba uko urubuga rukora…",
    "Read the privacy notice":"Soma itangazo ry'ibanga", "Explore":"Shakisha", "Questions":"Ibibazo", "Platform":"Urubuga", "Phone simulator":"Imyigishirizo kuri telefoni", "Resources":"Ibikoresho", "How reporting works":"Uko gutanga raporo bikora", "API reference":"Amabwiriza ya API", "Privacy notice":"Itangazo ry'ibanga",
    "Refreshed automatically":"Byongerwa mu buryo bwikora", "Back to top":"Subira hejuru", "Pilot starting":"Igerageza ritangiye", "Community voices matter":"Ijwi ry'abaturage riragira agaciro", "Be the first: dial *801#":"Ba uwa mbere: kanda *801#", "Waiting for the latest reports…":"Tegereza raporo ziheruka…", "Bugesera":"Bugesera", "sectors reporting":"imirenge itanga amakuru", "last 30 days":"iminsi 30 ishize",
    "Platform online ·":"Urubuga ruri ku murongo ·", "reports from the field":"raporo zavuye mu murima", "Platform offline · live figures paused":"Urubuga ntiruri ku murongo · imibare y'igihe nyacyo yahagaritswe", "Live reports appear here when the platform is running.":"Raporo z'igihe nyacyo zigaragara hano iyo urubuga rukora.",
    "Dial *801#":"Kanda *801#", "Main menu · press 2 for pests & disease":"Ibijyanye n'ingenzi · kanda 2 ku tunyangingo n'indwara", "Which crop? 2 = maize":"Igihingwa kihe? 2 = ibigori", "Which problem? 1 = fall armyworm":"Ni ikibazo kihe? 1 = nzana", "How severe? 5 = everything damaged":"Nkanshi? 5 = byangiritse byose", "Saved. Planners see a critical case straight away.":"Byabitswe. Abategura ingamba bahita babona ikibazo gikomeye."
  };

  let lang = localStorage.getItem("cs-ircfs-lang") === "rw" ? "rw" : "en";
  let textNodes = [];
  const originalTextNodes = new WeakMap();
  function collectTextNodes() {
    textNodes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.parentElement || node.parentElement.closest("script, style, code")) return NodeFilter.FILTER_REJECT;
        return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    let textNode;
    while ((textNode = walker.nextNode())) {
      if (!originalTextNodes.has(textNode)) originalTextNodes.set(textNode, textNode.textContent);
      textNodes.push({ node: textNode, en: originalTextNodes.get(textNode) });
    }
  }

  function applyLanguage(next) {
    lang = next;
    localStorage.setItem("cs-ircfs-lang", lang);
    document.documentElement.lang = lang === "rw" ? "rw" : "en";
    collectTextNodes();
    $("#langLabel").textContent = NAV[lang].label;
    links.querySelectorAll("a[data-nav]").forEach((a, i) => { a.textContent = NAV[lang].items[i]; });
    textNodes.forEach(({ node, en }) => {
      const key = en.trim();
      node.textContent = lang === "rw" && RW_COPY[key] ? RW_COPY[key] : en;
    });
    $("#langBtn").title = lang === "rw" ? "Hindura ujye mu Cyongereza" : "Hindurira mu Kinyarwanda";
    $("#langBtn").setAttribute("aria-label", lang === "rw" ? "Hindura urubuga mu Cyongereza" : "Hindura urubuga mu Kinyarwanda");
  }
  $("#langBtn").addEventListener("click", () => applyLanguage(lang === "en" ? "rw" : "en"));
  applyLanguage(lang);

  if ("IntersectionObserver" in window) {
    const navLinks = [...links.querySelectorAll("a[data-nav]")];
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => {
          const active = a.getAttribute("href") === `#${entry.target.id}`;
          a.classList.toggle("active", active);
          if (active) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    navLinks.forEach((a) => { const target = document.querySelector(a.getAttribute("href")); if (target) spy.observe(target); });
  }

  // ---------- Signed-in people go straight to the dashboard ----------
  if (session.account()) {
    const dashboardLabel = lang === "rw" ? "Fungura dashboard" : "Open dashboard";
    $("#nav-cta").innerHTML = `${dashboardLabel} <i class="bi bi-arrow-up-right" aria-hidden="true"></i>`;
    $("#hero-cta").innerHTML = `${dashboardLabel} <i class="bi bi-arrow-up-right" aria-hidden="true"></i>`;
    ["#nav-cta", "#hero-cta", "#mobile-cta"].forEach((id) => { const link = $(id); if (link) link.href = "/app/"; });
    const mobile = $("#mobile-cta"); if (mobile) mobile.textContent = lang === "rw" ? "Fungura dashboard" : "Open dashboard";
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
    if (seconds < 60) return lang === "rw" ? "ubu" : "just now";
    if (seconds < 3600) return lang === "rw" ? `iminota ${Math.floor(seconds / 60)} ishize` : `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return lang === "rw" ? `amasaha ${Math.floor(seconds / 3600)} ashize` : `${Math.floor(seconds / 3600)} h ago`;
    return lang === "rw" ? `iminsi ${Math.floor(seconds / 86400)} ishize` : `${Math.floor(seconds / 86400)} d ago`;
  }

  const KIND_ICON = { pest: "bug", fault: "tools", rain: "cloud-rain", harvest: "basket", water: "droplet", feedback: "chat-left-text", nutrition: "heart-pulse" };
  function setLive(online) {
    $("#hf-dot").classList.toggle("off", !online);
    document.querySelectorAll("[data-live-badge]").forEach((badge) => { badge.textContent = online ? (lang === "rw" ? "AMAKURU" : "LIVE") : (lang === "rw" ? "NTIRURIHO" : "OFFLINE"); badge.classList.toggle("off", !online); });
  }

  function renderHero(data) {
    // Before the first report, invite one instead of showing "0 farmer reports".
    $("#hero-reports").textContent = data.reports ? `${fmt(data.reports)} farmer report${data.reports === 1 ? "" : "s"}` : "Pilot starting";
    $("#hero-reports-note").textContent = data.demo_mode ? "Demonstration figures" : data.reports ? "Community voices matter" : "Be the first: dial *801#";
    $("#hero-feed").innerHTML = data.recent.length
      ? data.recent.slice(0, 3).map((item) => `<li class="${escapeHtml(item.kind)}"><i class="bi bi-${KIND_ICON[item.kind] || "clipboard-data"}" aria-hidden="true"></i><div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.sector || "Bugesera")} · ${ago(item.created_at)}</small></div></li>`).join("")
      : `<li class="hf-empty">${lang === "rw" ? "Igerageza ritangiye. Raporo zigaragara hano abahinzi bamaze gukanda *801# cyangwa kohereza ubutumwa kuri 8448." : "The pilot is starting. Reports appear here as soon as farmers dial *801# or text 8448."}</li>`;
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
    applyLanguage(lang);
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
      caption.textContent = lang === "rw" && RW_COPY[screen.caption] ? RW_COPY[screen.caption] : screen.caption;
      ussd.classList.remove("is-fading");
    }, 250);
    if (screen.key) {
      const key = keys.find((k) => k.textContent === screen.key);
      window.setTimeout(() => { key?.classList.add("press"); window.setTimeout(() => key?.classList.remove("press"), 350); }, 2300);
    }
    step = (step + 1) % SCREENS.length;
  }
  showScreen();
  let demoPaused = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const demoTimer = window.setInterval(() => { if (!document.hidden && !demoPaused) showScreen(); }, 2900);
  const demoToggle = $("#demo-toggle");
  if (demoToggle && demoPaused) {
    demoToggle.setAttribute("aria-pressed", "true");
    demoToggle.innerHTML = `<i class="bi bi-play-fill" aria-hidden="true"></i><span>${lang === "rw" ? "Komeza urugero" : "Play demo"}</span>`;
  }
  demoToggle?.addEventListener("click", () => {
    demoPaused = !demoPaused;
    demoToggle.setAttribute("aria-pressed", String(demoPaused));
    demoToggle.innerHTML = demoPaused ? `<i class="bi bi-play-fill" aria-hidden="true"></i><span>${lang === "rw" ? "Komeza urugero" : "Play demo"}</span>` : `<i class="bi bi-pause-fill" aria-hidden="true"></i><span>${lang === "rw" ? "Hagarika urugero" : "Pause demo"}</span>`;
  });

  refresh();
  window.setInterval(() => { if (!document.hidden) refresh(); }, 20000);
})();
