import type { MessageKey } from "./en";
import { assistantRw } from "./assistant";

/**
 * Kinyarwanda interface text. Keys that are missing fall back to English.
 * RW: needs field review — every string here must be checked by native-speaking field
 * staff before the pilot. Strings taken from the existing dashboard (shared.js) are
 * marked "existing"; the rest are first drafts.
 */
export const rw: Partial<Record<MessageKey, string>> = {
  ...assistantRw,
  "language.partial": "Amagambo amwe ari mu Cyongereza.", // draft: native review required
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
  "greet.morning": "Mwaramutse", // existing
  "greet.afternoon": "Mwiriwe", // existing
  "greet.evening": "Mwiriwe", // existing
  "greet.planner": "Mugenamigambi", // existing
  "hero.subtitle": "Ishusho isobanutse y'imikorere yo kuhira, ibyago ku bihingwa n'ibikorwa by'abaturage.", // existing
  "hero.openActNow": "Fungura Ibyihutirwa",
  "hero.map": "Ikarita y'akarere",
  "modules.title": "Fungura igice",
  "filter.scheme": "Umushinga", // existing
  "filter.allSchemes": "Imishinga yose", // existing
  "filter.refresh": "Vugurura", // existing
  "section.actions": "Ibikeneye gukorwa vuba", // existing
  "section.map": "Imvura n'inama zo kuhira",
  "advice.irrigate_more": "Izuba: uhire cyane",
  "advice.normal": "Bisanzwe",
  "advice.irrigate_less": "Imvura: uhire gake",
  "advice.no_data": "Nta makuru y'imvura",
  "map.reset": "Garura Bugesera yose", // existing
  "state.loading": "Biratangira…",
  "state.retry": "Ongera ugerageze",
  // Draft modernization strings: native-speaker approval required before pilot use.
  "climate.observedCoverage": "Imirenge ifite ibipimo by'imvura by'abaturage",
  "climate.forecastCoverage": "Imirenge ifite iteganyagihe",
  "climate.unrecordedCoverage": "Imirenge idafite ibipimo by'imvura",
  "map.cellBoundaries": "Imbibi z'utugari (iyo zanditswe)",
  "map.search": "Shakisha izina cyangwa uko raporo imeze",
  "map.observations": "Ibyanditswe ku ikarita",
  "map.searchBasis": "Ishakisha rigabanya ahari ibikorwaremezo, ibihingwa n'imvura. Ibindi byiciro ni incamake z'akarere. Imvura itazwi ni ikijuju; zeru yapimwe ni ubururu. Urutonde rukora n'iyo ikarita itabonetse.",
  "map.noMatches": "Nta byanditswe bihuye n'ibyo washakishije.",
  "activity.title": "Raporo n'ibimenyetso",
  "activity.note": "Umurenge, gahunda yo kuhira n'igihe biri hejuru birakoreshwa hano. Akagari, koperative n'amatariki bihindura iki gice gusa.",
  "activity.cell": "Akagari",
  "activity.allCells": "Utugari twose",
  "activity.cooperative": "Koperative",
  "activity.allCooperatives": "Koperative zose",
  "activity.start": "Zakiriwe kuva",
  "activity.end": "Zakiriwe kugeza",
  "activity.invalid": "Hitamo amatariki akurikirana atarenza iminsi 366.",
  "activity.optionsError": "Bimwe mu byo guhitamo ntibyabonetse; ibihari biracyakora.",
  "activity.reports": "Raporo zakiriwe",
  "activity.previous": "Igihe kibanziriza iki kingana na cyo",
  "activity.verified": "Raporo zagenzuwe",
  "activity.located": "Raporo zifite aho zandikiwe ku ikarita",
  "activity.change": "Impinduka mu mubare wa raporo zakiriwe: {n}",
  "activity.basis": "Amatariki yo mu Rwanda, hakurikijwe igihe raporo yakiriwe. Raporo z'igerageza ntizibarwa. Koperative ikoresha abanyamuryango bayo b'ubu. Umubare wa raporo si igipimo cy'ingaruka ku buhinzi; aho zandikiwe ntihamya ko aho hantu ari ho neza.",
};
