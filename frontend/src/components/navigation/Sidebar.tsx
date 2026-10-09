import { ArrowUpRight, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { NAV, type NavItem } from "./nav";

const linkClass = (active: boolean) =>
  cx(
    "group flex items-center gap-3 rounded-control px-3 py-2 text-sm font-semibold transition-colors",
    active ? "bg-white/15 text-white" : "text-white/75 hover:bg-white/10 hover:text-white",
  );

function Item({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const { t } = useI18n();
  const Icon = item.icon;
  const content = (
    <>
      <Icon aria-hidden className="h-[18px] w-[18px] shrink-0" />
      <span className="truncate">{t(item.label)}</span>
    </>
  );
  if (item.to) {
    return (
      <NavLink to={item.to} end onClick={onNavigate} className={({ isActive }) => linkClass(isActive)}>
        {content}
      </NavLink>
    );
  }
  return (
    <a href={item.href} className={linkClass(false)} title={`${t(item.label)} (${t("nav.classic")})`}>
      {content}
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
      <div className={cx("fixed inset-0 z-30 bg-forest/40 lg:hidden", open ? "block" : "hidden")} onClick={onClose} aria-hidden />
      <aside
        id="app-sidebar"
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-forest text-white transition-transform lg:translate-x-0",
          // Closed on small screens: off-canvas and invisible, so its links leave the tab order.
          open ? "visible translate-x-0" : "invisible -translate-x-full lg:visible",
        )}
      >
        <div className="flex items-center gap-3 px-5 pb-4 pt-5">
          <img src="/app/branding/logo-96.png" alt="" width={40} height={40} className="h-10 w-10 rounded-full bg-white p-0.5" />
          <div className="min-w-0">
            <p className="font-heading text-lg font-extrabold leading-tight tracking-tight">{t("app.name")}</p>
            <p className="truncate text-2xs text-white/65">{t("app.tagline")}</p>
          </div>
          <button type="button" onClick={onClose} className="ml-auto rounded-control p-2 text-white/80 hover:bg-white/10 lg:hidden">
            <X aria-hidden className="h-5 w-5" />
            <span className="sr-only">{t("nav.close")}</span>
          </button>
        </div>
        <nav aria-label={t("nav.menu")} className="flex-1 space-y-5 overflow-y-auto px-3 pb-6">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="px-3 pb-1.5 text-2xs font-bold uppercase tracking-[0.14em] text-white/45">{t(group.label)}</p>
              <ul className="space-y-0.5">
                {group.items.map((item) => (
                  <li key={item.label}>
                    <Item item={item} onNavigate={onClose} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
