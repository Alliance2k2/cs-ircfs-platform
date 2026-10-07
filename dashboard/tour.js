// Guided presentation tour: spotlights one section at a time with a short explanation.
(function () {
  let steps = [];
  let index = 0;
  let spotlight;
  let card;

  function close() {
    spotlight?.remove();
    card?.remove();
    spotlight = card = null;
    document.removeEventListener("keydown", onKey);
    window.removeEventListener("resize", place);
    window.removeEventListener("scroll", place);
  }

  function onKey(event) {
    if (event.key === "Escape") close();
    if (event.key === "ArrowRight") go(index + 1);
    if (event.key === "ArrowLeft") go(index - 1);
  }

  function place() {
    const target = document.querySelector(steps[index].target);
    if (!target || !spotlight) return;
    const rect = target.getBoundingClientRect();
    const pad = 8;
    const top = Math.max(8, rect.top - pad);
    const height = Math.min(rect.height + pad * 2, window.innerHeight - top - 8);
    Object.assign(spotlight.style, { top: `${top}px`, left: `${rect.left - pad}px`, width: `${rect.width + pad * 2}px`, height: `${height}px` });
    const cardHeight = card.offsetHeight;
    const below = top + height + 14;
    const cardTop = below + cardHeight < window.innerHeight ? below : Math.max(12, top - cardHeight - 14);
    const cardLeft = Math.min(Math.max(12, rect.left), window.innerWidth - card.offsetWidth - 12);
    Object.assign(card.style, { top: `${cardTop}px`, left: `${cardLeft}px` });
  }

  function go(next) {
    if (next < 0) return;
    if (next >= steps.length) { close(); return; }
    index = next;
    const step = steps[index];
    const target = document.querySelector(step.target);
    if (!target) { go(index + 1); return; }
    target.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    const escape = window.CS?.escapeHtml || ((v) => v);
    card.innerHTML = `<p class="tour-step">STEP ${index + 1} OF ${steps.length}</p><h3>${escape(step.title)}</h3><p>${escape(step.text)}</p>
      <div class="tour-actions"><span class="tour-dots">${steps.map((_, i) => `<i class="${i === index ? "on" : ""}"></i>`).join("")}</span>
      <div><button type="button" data-tour="close">Exit</button>${index ? '<button type="button" data-tour="back">Back</button>' : ""}<button type="button" class="primary" data-tour="next">${index === steps.length - 1 ? "Finish" : "Next →"}</button></div></div>`;
    card.querySelector('[data-tour="next"]').focus();
    window.setTimeout(place, 380);
    place();
  }

  function start(tourSteps) {
    close();
    steps = tourSteps;
    spotlight = document.createElement("div");
    spotlight.className = "tour-spotlight";
    card = document.createElement("div");
    card.className = "tour-card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-label", "Presentation tour");
    card.addEventListener("click", (event) => {
      const action = event.target.dataset.tour;
      if (action === "close") close();
      if (action === "back") go(index - 1);
      if (action === "next") go(index + 1);
    });
    document.body.append(spotlight, card);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, { passive: true });
    go(0);
  }

  window.CSTour = { start, close };
})();
