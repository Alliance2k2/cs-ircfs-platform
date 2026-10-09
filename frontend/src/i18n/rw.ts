import type { MessageKey } from "./en";

/**
 * Kinyarwanda interface text. Keys that are missing fall back to English.
 * RW: needs field review — every string here must be checked by native-speaking field
 * staff before the pilot. Strings taken from the existing dashboard (shared.js) are
 * marked "existing"; the rest are first drafts.
 */
export const rw: Partial<Record<MessageKey, string>> = {
  "app.skip": "Jya ku bikubiyemo",
  "nav.group.dashboard": "Imbonerahamwe",
  "nav.group.field": "Amakuru yo mu murima",
  "nav.group.platform": "Urubuga",
  "nav.overview": "Incamake", // existing
  "nav.actnow": "Ibyihutirwa", // existing
  "nav.channels": "Ubutumwa bwo mu murima", // existing
  "nav.schemes": "Imikorere y'imishinga", // existing
  "nav.advice": "Inama zo kuhira", // existing
  "nav.food": "Imirire y'ingo", // existing
  "nav.map": "Ikarita n'ibyagaragaye", // existing
  "nav.feedback": "Ibitekerezo by'abaturage", // existing
  "nav.management": "Gucunga urubuga", // existing
  "nav.simulator": "Igerageza rya telefoni", // existing
  "nav.home": "Ahabanza", // existing
  "lang.label": "Ururimi", // existing
  "account.signout": "Sohoka", // existing
  "overview.title": "Ibibera i Bugesera",
  "filter.scheme": "Umushinga", // existing
  "filter.allSchemes": "Imishinga yose", // existing
  "filter.refresh": "Vugurura", // existing
  "section.actions": "Ibikeneye gukorwa vuba", // existing
  "section.map": "Imvura n'inama zo kuhira",
  "advice.irrigate_more": "Izuba: uhire cyane",
  "advice.normal": "Bisanzwe",
  "advice.reduce": "Imvura: uhire gake",
  "advice.no_data": "Nta makuru y'imvura",
  "map.reset": "Garura Bugesera yose", // existing
  "state.loading": "Biratangira…",
  "state.retry": "Ongera ugerageze",
};
