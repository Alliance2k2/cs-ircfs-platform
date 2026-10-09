import type { Language } from "@/i18n";
import { translate } from "@/i18n";

const locale = (lang: Language) => (lang === "rw" ? "rw-RW" : "en-GB");

/** Server timestamps from SQLite have no zone; they are UTC. */
export function parseTimestamp(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
}

export function formatNumber(value: number, lang: Language, digits = 1): string {
  return new Intl.NumberFormat(locale(lang), { maximumFractionDigits: digits }).format(value);
}

export function formatDate(value: string, lang: Language): string {
  return new Intl.DateTimeFormat(locale(lang), { day: "numeric", month: "short", timeZone: "Africa/Kigali" }).format(parseTimestamp(value));
}

export function formatTime(value: Date, lang: Language): string {
  return new Intl.DateTimeFormat(locale(lang), { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Kigali" }).format(value);
}

export function relativeTime(value: string, lang: Language, now: number = Date.now()): string {
  const seconds = Math.max(0, (now - parseTimestamp(value).getTime()) / 1000);
  if (seconds < 60) return translate(lang, "time.justNow");
  if (seconds < 3600) return translate(lang, "time.minutes", { n: Math.floor(seconds / 60) });
  if (seconds < 86400) return translate(lang, "time.hours", { n: Math.floor(seconds / 3600) });
  return translate(lang, "time.days", { n: Math.floor(seconds / 86400) });
}

/** "%" sits on the number; every other unit is written after it. */
export function withUnit(text: string, unit: string): { value: string; unit: string } {
  return unit === "%" ? { value: `${text}%`, unit: "" } : { value: text, unit };
}
