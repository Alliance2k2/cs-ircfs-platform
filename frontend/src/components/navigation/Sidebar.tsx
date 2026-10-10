import { ArrowUpRight, ChevronsLeft, ChevronsRight, Radio, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { canAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { NAV, type NavItem } from "./nav";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

function Item({ item, collapsed, onNavigate }: { item: NavItem; collapsed: boolean; onNavigate?: () => void }) {
  const { t } = useI18n();
  const Icon = item.icon;
  const label = t(item.label);
  const body = (active: boolean) => (
    <>
      <span aria-hidden className={cx("grid h-8 w-8 shrink-0 place-items-center rounded-lg", active ? "bg-white/20" : "bg-white/5 group-hover:bg-white/10")}>
        <Icon className="h-[18px] w-[18px]" />
      </span>
      <span className={cx("truncate", collapsed && "lg:sr-only")}>{label}</span>
      {active && !collapsed && <span aria-hidden className="ml-auto h-2 w-2 rounded-full bg-lime" />}
    </>
  );
  const base = (active: boolean) =>
    cx(
      "group flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-semibold transition",
      collapsed && "lg:justify-center lg:px-0",
      active ? "bg-gradient-to-r from-fresh to-primary text-white shadow-[0_8px_20px_rgb(0_0_0/0.18)]" : "text-white/80 hover:bg-white/10 hover:text-white",
    );
  if (item.to) {
    return (
      <NavLink to={item.to} end={item.to === "/"} onClick={onNavigate} className={({ isActive }) => base(isActive)} title={collapsed ? label : undefined}>
        {({ isActive }) => body(isActive)}
      </NavLink>
    );
  }
  return (
    <a href={item.href} className={base(false)} title={label}>
      {body(false)}
      {!collapsed && <ArrowUpRight aria-hidden className="ml-auto h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-60" />}
    </a>
  );
}

/** Fixed on large screens (full or icons only); a drawer on phones and tablets. */
export function Sidebar({ open, onClose, collapsed, onToggleCollapsed }: SidebarProps) {
  const { t } = useI18n();
  const { role } = useSession();
  const groups = NAV.map((group) => ({ ...group, items: group.items.filter((item) => canAccess(role, item.access)) })).filter((group) => group.items.length);

  return (
    <>
      <div className={cx("fixed inset-0 z-30 bg-forest/50 lg:hidden", open ? "block" : "hidden")} onClick={onClose} aria-hidden />
      <aside
        id="app-sidebar"
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-gradient-to-b from-forest-light via-forest to-forest-deep text-white transition-[transform,width] duration-200",
          collapsed ? "lg:w-20" : "lg:w-72",
          // Closed on small screens: off-canvas and invisible, so its links leave the tab order.
          open ? "visible translate-x-0" : "invisible -translate-x-full lg:visible lg:translate-x-0",
        )}
      >
        <div className={cx("flex items-center gap-3 border-b border-white/10 px-5 pb-4 pt-5", collapsed && "lg:justify-center lg:px-2")}>
          <img src="/app/branding/logo-96.png" alt="" width={44} height={44} className="h-11 w-11 shrink-0 rounded-full bg-white p-0.5 shadow-[0_6px_16px_rgb(0_0_0/0.25)]" />
          <div className={cx("min-w-0", collapsed && "lg:hidden")}>
            <p className="font-heading text-lg font-extrabold leading-tight tracking-tight">{t("app.name")}</p>
            <p className="truncate text-2xs text-white/65">{t("app.tagline")}</p>
          </div>
          <button type="button" onClick={onClose} className="ml-auto rounded-control p-2 text-white/80 hover:bg-white/10 lg:hidden">
            <X aria-hidden className="h-5 w-5" />
            <span className="sr-only">{t("nav.close")}</span>
          </button>
        </div>

        <nav aria-label={t("nav.menu")} className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
          {groups.map((group) => (
            <div key={group.label}>
              <p className={cx("flex items-center gap-2 px-2.5 pb-1.5 text-2xs font-bold uppercase tracking-[0.14em] text-white/45", collapsed && "lg:sr-only")}>
                {t(group.label)}
                <span aria-hidden className="h-px flex-1 bg-white/10" />
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => (
                  <li key={item.label}>
                    <Item item={item} collapsed={collapsed} onNavigate={onClose} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className={cx("m-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3", collapsed && "lg:hidden")}>
          <span aria-hidden className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lime text-forest">
            <Radio className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-bold">{t("side.channels")}</span>
            <span className="block truncate text-2xs text-white/65">{t("side.channelsNote")}</span>
          </span>
        </div>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-expanded={!collapsed}
          className="hidden items-center justify-center gap-2 border-t border-white/10 py-3 text-xs font-semibold text-white/70 hover:bg-white/5 hover:text-white lg:flex"
        >
          {collapsed ? <ChevronsRight aria-hidden className="h-4 w-4" /> : <ChevronsLeft aria-hidden className="h-4 w-4" />}
          <span className={cx(collapsed && "sr-only")}>{t(collapsed ? "nav.expand" : "nav.collapse")}</span>
        </button>
      </aside>
    </>
  );
}
