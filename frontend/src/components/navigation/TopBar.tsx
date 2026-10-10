import { useQuery } from "@tanstack/react-query";
import { Bell, CalendarDays, ChevronDown, ChevronRight, Globe, LogOut, Menu, Search } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useOverview } from "@/features/overview/useOverview";
import { useI18n, type Language } from "@/i18n";
import { cx } from "@/lib/cx";
import { relativeTime } from "@/lib/format";
import { API_BASE } from "@/services/api/client";
import { CommandPalette } from "./CommandPalette";
import { ROUTES } from "./nav";

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
  return name.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("");
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

/** A button that opens a small panel; closes on Escape or a click elsewhere. */
function Popover({ label, button, children, align = "right" }: { label: string; button: ReactNode; children: (close: () => void) => ReactNode; align?: "left" | "right" }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return (
    <div ref={root} className="relative">
      <button type="button" aria-expanded={open} aria-haspopup="true" aria-label={label} onClick={() => setOpen((value) => !value)} className="flex items-center rounded-full">
        {button}
      </button>
      {open && (
        <div className={cx("absolute top-full z-30 mt-2 w-80 rounded-card border border-line bg-surface p-2 shadow-raised", align === "right" ? "right-0" : "left-0")}>
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { t, lang, setLang } = useI18n();
  const { account, role, development } = useSession();
  const location = useLocation();
  const online = usePlatformOnline();
  const [palette, setPalette] = useState(false);
  // Shares the cache of the default overview, so the bell costs no extra request.
  const overview = useOverview({ days: 30, schemeId: null, sectorId: null }, isStaff(role));
  const actions = overview.data?.priority_actions ?? [];
  const openCount = overview.data ? overview.data.counts.open_cases + overview.data.counts.open_grievances : null;
  const name = account?.full_name || account?.email || t("account.local");
  const route = ROUTES.find((item) => item.to === location.pathname) ?? ROUTES[0]!;
  const today = new Intl.DateTimeFormat(lang === "rw" ? "rw-RW" : "en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "Africa/Kigali" }).format(new Date());
  const roleLabel = development ? t("account.localNote") : role.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPalette(true);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-2 border-b border-line bg-surface/95 px-3 backdrop-blur sm:gap-3 sm:px-6">
      <button type="button" onClick={onMenu} className="rounded-control p-2 text-forest hover:bg-canvas lg:hidden" aria-controls="app-sidebar">
        <Menu aria-hidden className="h-5 w-5" />
        <span className="sr-only">{t("nav.menu")}</span>
      </button>

      <nav aria-label={t("crumb.label")} className="hidden min-w-0 md:block">
        <ol className="flex items-center gap-1.5 text-sm">
          <li className="text-muted">{t("crumb.root")}</li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5 text-muted" /></li>
          <li className="text-muted">{t(route.group)}</li>
          <li aria-hidden><ChevronRight className="h-3.5 w-3.5 text-muted" /></li>
          <li aria-current="page" className="truncate font-bold text-forest">{t(route.label)}</li>
        </ol>
      </nav>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2.5">
        <button type="button" onClick={() => setPalette(true)} className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-muted hover:border-primary/40 hover:text-forest">
          <Search aria-hidden className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{t("shell.search")}</span>
          <kbd className="hidden rounded border border-line px-1 text-2xs xl:inline">Ctrl K</kbd>
        </button>
        <span className="hidden items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink 2xl:inline-flex">
          <CalendarDays aria-hidden className="h-3.5 w-3.5 text-muted" />
          {today}
        </span>
        {online !== null && (
          <span role="status" className={cx("hidden items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold lg:inline-flex",
            online ? "border-fresh/40 bg-mint text-primary-strong" : "border-critical/30 bg-critical-soft text-critical")}>
            <span aria-hidden className={cx("h-2 w-2 rounded-full", online ? "bg-fresh" : "bg-critical")} />
            {online ? t("top.online") : t("top.offline")}
          </span>
        )}

        {isStaff(role) && (
          <Popover
            label={t("top.alerts", { n: openCount ?? 0 })}
            button={
              <span className="relative rounded-full border border-line p-2 text-forest hover:bg-canvas">
                <Bell aria-hidden className="h-[18px] w-[18px]" />
                {openCount !== null && openCount > 0 && (
                  <span aria-hidden className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-critical px-1 text-2xs font-bold text-white">
                    {openCount > 99 ? "99+" : openCount}
                  </span>
                )}
              </span>
            }
          >
            {(close) => (
              <div>
                <p className="px-2 py-1.5 text-2xs font-bold uppercase tracking-wider text-muted">{t("shell.notifications")}</p>
                {actions.length === 0 ? (
                  <p className="px-2 py-3 text-sm text-muted">{t("shell.noNotifications")}</p>
                ) : (
                  <ul className="max-h-72 overflow-y-auto">
                    {actions.slice(0, 6).map((action) => (
                      <li key={`${action.item_type}-${action.item_id}`}>
                        <Link to={`/actions?open=${action.item_type}-${action.item_id}`} onClick={close} className="block rounded-control px-2 py-2 hover:bg-canvas">
                          <span className="block truncate text-sm font-semibold text-ink">{action.title}</span>
                          <span className="text-xs text-muted">
                            {t(`priority.${action.priority as "critical" | "high" | "medium"}`)} · {action.sector ?? ""} · {relativeTime(action.created_at, lang)}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
                <Link to="/actions" onClick={close} className="mt-1 block rounded-control px-2 py-2 text-sm font-semibold text-primary hover:bg-canvas">
                  {t("shell.allActions")} →
                </Link>
              </div>
            )}
          </Popover>
        )}

        <div role="group" aria-label={t("lang.label")} className="flex rounded-full border border-line p-0.5">
          {(["en", "rw"] as Language[]).map((code) => (
            <button key={code} type="button" aria-pressed={lang === code} onClick={() => setLang(code)}
              className={cx("rounded-full px-2.5 py-1 text-xs font-bold", lang === code ? "bg-forest text-white" : "text-muted hover:text-forest")}>
              {code.toUpperCase()}
            </button>
          ))}
        </div>

        <Popover
          label={t("shell.profile")}
          button={
            <span className="flex items-center gap-2">
              <span aria-hidden className="grid h-9 w-9 place-items-center rounded-full bg-mint font-heading text-sm font-extrabold text-forest">{initials(name)}</span>
              <span className="hidden min-w-0 text-left leading-tight lg:block">
                <span className="block max-w-[11rem] truncate text-sm font-bold text-ink">{name}</span>
                <span className="block text-2xs text-muted">{roleLabel}</span>
              </span>
              <ChevronDown aria-hidden className="hidden h-4 w-4 text-muted lg:block" />
            </span>
          }
        >
          {() => (
            <div className="space-y-1">
              <div className="rounded-control bg-canvas px-3 py-2.5 text-sm">
                <p className="font-bold text-ink">{name}</p>
                {account && <p className="truncate text-xs text-muted">{account.email}</p>}
                <p className="mt-1 text-xs text-muted">{t("shell.role")}: {roleLabel}</p>
                {account && <p className="text-xs text-muted">{t("shell.area")}: {account.area}</p>}
              </div>
              <a href="/" className="flex items-center gap-2 rounded-control px-3 py-2 text-sm text-ink hover:bg-canvas">
                <Globe aria-hidden className="h-4 w-4 text-muted" />
                {t("footer.public")}
              </a>
              {!development && (
                <button type="button" onClick={signOut} className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm font-semibold text-critical hover:bg-critical-soft">
                  <LogOut aria-hidden className="h-4 w-4" />
                  {t("account.signout")}
                </button>
              )}
            </div>
          )}
        </Popover>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </header>
  );
}
