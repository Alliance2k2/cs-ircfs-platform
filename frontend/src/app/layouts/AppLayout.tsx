import { Wrench } from "lucide-react";
import { Suspense, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { ErrorBoundary } from "@/app/ErrorBoundary";
import { useSession } from "@/app/providers/SessionProvider";
import { DataState } from "@/components/feedback/DataState";
import { AppFooter } from "@/components/navigation/AppFooter";
import { Sidebar } from "@/components/navigation/Sidebar";
import { TopBar } from "@/components/navigation/TopBar";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";

const COLLAPSED_KEY = "cs_ircfs_sidebar_collapsed";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function AppLayout() {
  const { t, lang } = useI18n();
  const { development } = useSession();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(readCollapsed);

  const toggleCollapsed = () =>
    setCollapsed((value) => {
      try {
        window.localStorage.setItem(COLLAPSED_KEY, value ? "0" : "1");
      } catch {
        /* storage blocked: the choice lasts for this visit only */
      }
      return !value;
    });

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-2 focus:font-semibold">
        {t("app.skip")}
      </a>
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
      <div className={cx("transition-[padding] duration-200", collapsed ? "lg:pl-20" : "lg:pl-72")}>
        <TopBar onMenu={() => setMenuOpen(true)} />
        {development && (
          <p className="flex items-center gap-2 border-b border-line bg-water-soft px-4 py-2 text-xs font-semibold text-water sm:px-6">
            <Wrench aria-hidden className="h-4 w-4 shrink-0" />
            {t("banner.local")}
          </p>
        )}
        <main id="main" className="mx-auto max-w-[1400px] px-4 pb-10 pt-6 sm:px-6">
          <ErrorBoundary lang={lang} resetKey={location.pathname}>
            <Suspense fallback={<DataState kind="loading" />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
        <AppFooter />
      </div>
    </div>
  );
}
