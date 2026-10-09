import { LogOut, Menu } from "lucide-react";
import { useSession } from "@/app/providers/SessionProvider";
import { useI18n, type Language } from "@/i18n";
import { API_BASE } from "@/services/api/client";

async function signOut() {
  await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "same-origin" }).catch(() => null);
  try {
    // The legacy pages also keep the token in sessionStorage; clear it so they sign out too.
    window.sessionStorage.removeItem("cs_ircfs_session");
    window.sessionStorage.removeItem("cs_ircfs_account");
  } catch {
    /* storage blocked */
  }
  window.location.assign("/login.html");
}

function initials(name: string): string {
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { t, lang, setLang } = useI18n();
  const { account, role, development } = useSession();
  const name = account?.full_name || account?.email || t("account.local");

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-surface/95 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onMenu}
        className="rounded-control p-2 text-forest hover:bg-canvas lg:hidden"
        aria-controls="app-sidebar"
      >
        <Menu aria-hidden className="h-5 w-5" />
        <span className="sr-only">{t("nav.menu")}</span>
      </button>

      <div className="ml-auto flex items-center gap-3">
        <div role="group" aria-label={t("lang.label")} className="flex rounded-control border border-line p-0.5">
          {(["en", "rw"] as Language[]).map((code) => (
            <button
              key={code}
              type="button"
              aria-pressed={lang === code}
              onClick={() => setLang(code)}
              className={`rounded-[7px] px-2.5 py-1 text-xs font-bold ${lang === code ? "bg-forest text-white" : "text-muted hover:text-forest"}`}
            >
              {code.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2.5">
          <span aria-hidden className="grid h-9 w-9 place-items-center rounded-full bg-mint font-heading text-sm font-extrabold text-forest">
            {initials(name)}
          </span>
          <div className="hidden min-w-0 leading-tight sm:block">
            <p className="max-w-[12rem] truncate text-sm font-bold text-ink">{name}</p>
            <p className="text-2xs text-muted">{development ? t("account.localNote") : role.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase())}</p>
          </div>
        </div>

        {!development && (
          <button type="button" onClick={signOut} className="rounded-control p-2 text-muted hover:bg-canvas hover:text-forest">
            <LogOut aria-hidden className="h-[18px] w-[18px]" />
            <span className="sr-only">{t("account.signout")}</span>
          </button>
        )}
      </div>
    </header>
  );
}
