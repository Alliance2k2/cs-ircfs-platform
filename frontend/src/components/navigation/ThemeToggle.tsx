import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
// Restore the white-and-green default; only a new explicit choice enables dark mode.
const STORAGE_KEY="cs-ircfs-theme-v2";
export function ThemeToggle(){
  const {t}=useI18n();
  const [dark,setDark]=useState(()=>{
    try {
      const value=window.localStorage.getItem(STORAGE_KEY);
      return value === "dark";
    }catch{return false;}
  });
  useEffect(()=>{document.documentElement.dataset.theme=dark?"dark":"light";},[dark]);
  const toggle=()=>setDark(current=>{
    const next=!current;
    try{window.localStorage.setItem(STORAGE_KEY,next?"dark":"light");}catch{/* Theme still works without storage. */}
    return next;
  });
  const Icon=dark?Sun:Moon;
  return <button type="button" aria-label={t("theme.dark")} aria-pressed={dark} title={dark?t("theme.useLight"):t("theme.useDark")}
    onClick={toggle} className="grid h-9 w-9 shrink-0 place-items-center rounded-control border border-line text-ink hover:bg-canvas">
    <Icon className="h-4 w-4" aria-hidden/>
  </button>;
}
