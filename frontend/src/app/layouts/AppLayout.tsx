import { Wrench } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useSession } from "@/app/providers/SessionProvider";
import { AppFooter } from "@/components/navigation/AppFooter";
import { Sidebar } from "@/components/navigation/Sidebar";
import { TopBar } from "@/components/navigation/TopBar";
import { useI18n } from "@/i18n";

export function AppLayout() {
  const { t } = useI18n();
  const { development } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-2 focus:font-semibold">
        {t("app.skip")}
      </a>
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="lg:pl-72">
        <TopBar onMenu={() => setMenuOpen(true)} />
        {development && (
          <p className="flex items-center gap-2 border-b border-line bg-water-soft px-4 py-2 text-xs font-semibold text-water sm:px-6">
            <Wrench aria-hidden className="h-4 w-4 shrink-0" />
            {t("banner.local")}
          </p>
        )}
        <main id="main" className="mx-auto max-w-[1400px] px-4 pb-10 pt-6 sm:px-6">
          <Outlet />
        </main>
        <AppFooter />
      </div>
    </div>
  );
}
