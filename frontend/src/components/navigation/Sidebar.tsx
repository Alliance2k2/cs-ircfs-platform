import { ArrowUpRight, Radio, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { NAV, type NavItem } from "./nav";

const linkClass = (active: boolean) =>
  cx(
    "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition",
    active
      ? "bg-gradient-to-r from-fresh to-primary text-white shadow-[0_8px_20px_rgb(0_0_0/0.18)]"
      : "text-white/80 hover:bg-white/10 hover:text-white",
  );

function Item({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const { t } = useI18n();
  const Icon = item.icon;
  const content = (active: boolean) => (
    <>
      <span
        aria-hidden
        className={cx("grid h-8 w-8 shrink-0 place-items-center rounded-lg", active ? "bg-white/20" : "bg-white/5 group-hover:bg-white/10")}
      >
        <Icon className="h-[18px] w-[18px]" />
      </span>
      <span className="truncate">{t(item.label)}</span>
      {active && <span aria-hidden className="ml-auto h-2 w-2 rounded-full bg-lime" />}
    </>
  );
  if (item.to) {
    return (
      <NavLink to={item.to} end onClick={onNavigate} className={({ isActive }) => linkClass(isActive)}>
        {({ isActive }) => content(isActive)}
      </NavLink>
    );
  }
  return (
    <a href={item.href} className={linkClass(false)} title={`${t(item.label)} (${t("nav.classic")})`}>
      {content(false)}
      <ArrowUpRight aria-hidden className="ml-auto h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-60" />
    </a>
  );
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

/** Fixed on large screens; a drawer on phones and tablets. */
export function Sidebar({ open, onClose }: SidebarProps) {
  const { t } = useI18n();
  const { role } = useSession();
  const groups = NAV.map((group) => ({ ...group, items: group.items.filter((item) => !item.staffOnly || isStaff(role)) }));

  return (
    <>
      <div className={cx("fixed inset-0 z-30 bg-forest/50 lg:hidden", open ? "block" : "hidden")} onClick={onClose} aria-hidden />
      <aside
        id="app-sidebar"
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-gradient-to-b from-forest-light via-forest to-forest-deep text-white transition-transform lg:translate-x-0",
          // Closed on small screens: off-canvas and invisible, so its links leave the tab order.
          open ? "visible translate-x-0" : "invisible -translate-x-full lg:visible",
        )}
      >
        <div className="flex items-center gap-3 border-b border-white/10 px-5 pb-4 pt-5">
          <img src="/app/branding/logo-96.png" alt="" width={44} height={44} className="h-11 w-11 rounded-full bg-white p-0.5 shadow-[0_6px_16px_rgb(0_0_0/0.25)]" />
          <div className="min-w-0">
            <p className="font-heading text-lg font-extrabold leading-tight tracking-tight">{t("app.name")}</p>
            <p className="truncate text-2xs text-white/65">{t("app.tagline")}</p>
          </div>
          <button type="button" onClick={onClose} className="ml-auto rounded-control p-2 text-white/80 hover:bg-white/10 lg:hidden">
            <X aria-hidden className="h-5 w-5" />
            <span className="sr-only">{t("nav.close")}</span>
          </button>
        </div>

        <nav aria-label={t("nav.menu")} className="flex-1 space-y-5 overflow-y-auto px-3 py-5">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="flex items-center gap-2 px-3 pb-2 text-2xs font-bold uppercase tracking-[0.14em] text-white/45">
                {t(group.label)}
                <span aria-hidden className="h-px flex-1 bg-white/10" />
              </p>
              <ul className="space-y-1">
                {group.items.map((item) => (
                  <li key={item.label}>
                    <Item item={item} onNavigate={onClose} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="m-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3">
          <span aria-hidden className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lime text-forest">
            <Radio className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-bold">{t("side.channels")}</span>
            <span className="block truncate text-2xs text-white/65">{t("side.channelsNote")}</span>
          </span>
        </div>
      </aside>
    </>
  );
}
