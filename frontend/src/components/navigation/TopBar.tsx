import { useQuery } from "@tanstack/react-query";
import { Bell, CalendarDays, ChevronRight, LogOut, Menu } from "lucide-react";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useOverview } from "@/features/overview/useOverview";
import { useI18n, type Language } from "@/i18n";
import { cx } from "@/lib/cx";
import { API_BASE } from "@/services/api/client";

async function signOut() {
  await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "same-origin" }).catch(() => null);
  try {
    // The classic pages also keep the token in sessionStorage; clear it so they sign out too.
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

/** Whether the API answers its health check (refreshed every minute). */
function usePlatformOnline(): boolean | null {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async ({ signal }) => (await fetch("/health", { signal })).ok,
    refetchInterval: 60_000,
    retry: false,
  });
  return health.isPending ? null : health.data === true;
}

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { t, lang, setLang } = useI18n();
  const { account, role, development } = useSession();
  const online = usePlatformOnline();
  // Shares the cache of the default overview, so the bell costs no extra request.
  const overview = useOverview({ days: 30, schemeId: null, sectorId: null });
  const openActions = overview.data ? overview.data.counts.open_cases + overview.data.counts.open_grievances : null;
  const name = account?.full_name || account?.email || t("account.local");
  const today = new Intl.DateTimeFormat(lang === "rw" ? "rw-RW" : "en-GB", {
    weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "Africa/Kigali",
  }).format(new Date());

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-surface/95 px-4 backdrop-blur sm:px-6">
      <button type="button" onClick={onMenu} className="rounded-control p-2 text-forest hover:bg-canvas lg:hidden" aria-controls="app-sidebar">
        <Menu aria-hidden className="h-5 w-5" />
        <span className="sr-only">{t("nav.menu")}</span>
      </button>

      <nav aria-label={t("crumb.label")} className="hidden min-w-0 md:block">
        <ol className="flex items-center gap-1.5 text-sm">
          <li className="text-muted">{t("crumb.root")}</li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5 text-muted" /></li>
          <li className="text-muted">{t("nav.group.dashboard")}</li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5 text-muted" /></li>
          <li aria-current="page" className="font-bold text-forest">{t("nav.overview")}</li>
        </ol>
      </nav>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <span className="hidden items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink xl:inline-flex">
          <CalendarDays aria-hidden className="h-3.5 w-3.5 text-muted" />
          {today}
        </span>
        {online !== null && (
          <span
            role="status"
            className={cx(
              "hidden items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold sm:inline-flex",
              online ? "border-fresh/40 bg-mint text-primary-strong" : "border-critical/30 bg-critical-soft text-critical",
            )}
          >
            <span aria-hidden className={cx("h-2 w-2 rounded-full", online ? "bg-fresh" : "bg-critical")} />
            {online ? t("top.online") : t("top.offline")}
          </span>
        )}
        {isStaff(role) && (
          <a href="/act-now.html" className="relative rounded-full border border-line p-2 text-forest hover:bg-canvas">
            <Bell aria-hidden className="h-[18px] w-[18px]" />
            <span className="sr-only">{t("top.alerts", { n: openActions ?? 0 })}</span>
            {openActions !== null && openActions > 0 && (
              <span aria-hidden className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-critical px-1 text-2xs font-bold text-white">
                {openActions > 99 ? "99+" : openActions}
              </span>
            )}
          </a>
        )}

        <div role="group" aria-label={t("lang.label")} className="flex rounded-full border border-line p-0.5">
          {(["en", "rw"] as Language[]).map((code) => (
            <button
              key={code}
              type="button"
              aria-pressed={lang === code}
              onClick={() => setLang(code)}
              className={cx("rounded-full px-2.5 py-1 text-xs font-bold", lang === code ? "bg-forest text-white" : "text-muted hover:text-forest")}
            >
              {code.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2.5">
          <span aria-hidden className="grid h-9 w-9 place-items-center rounded-full bg-mint font-heading text-sm font-extrabold text-forest">
            {initials(name)}
          </span>
          <div className="hidden min-w-0 leading-tight lg:block">
            <p className="max-w-[12rem] truncate text-sm font-bold text-ink">{name}</p>
            <p className="text-2xs text-muted">{development ? t("account.localNote") : role.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase())}</p>
          </div>
        </div>

        {!development && (
          <button type="button" onClick={signOut} className="rounded-full p-2 text-muted hover:bg-canvas hover:text-forest">
            <LogOut aria-hidden className="h-[18px] w-[18px]" />
            <span className="sr-only">{t("account.signout")}</span>
          </button>
        )}
      </div>
    </header>
  );
}
