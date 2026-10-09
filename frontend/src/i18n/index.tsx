import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en, type MessageKey } from "./en";
import { rw } from "./rw";

export type Language = "en" | "rw";
const STORAGE_KEY = "cs_ircfs_lang"; // shared with the legacy pages (dashboard/assets/js/shared.js)

type Translate = (key: MessageKey, values?: Record<string, string | number>) => string;
interface I18nValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: Translate;
}

const I18nContext = createContext<I18nValue | null>(null);

function storedLanguage(): Language {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "rw" ? "rw" : "en";
  } catch {
    return "en"; // storage blocked: keep working in English
  }
}

export function translate(lang: Language, key: MessageKey, values?: Record<string, string | number>): string {
  const text = (lang === "rw" ? rw[key] : undefined) ?? en[key];
  return values ? text.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match)) : text;
}

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Language }) {
  const [lang, setLangState] = useState<Language>(() => initial ?? storedLanguage());

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage blocked */
    }
  }, []);

  const value = useMemo<I18nValue>(() => ({ lang, setLang, t: (key, values) => translate(lang, key, values) }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside <I18nProvider>");
  return value;
}
