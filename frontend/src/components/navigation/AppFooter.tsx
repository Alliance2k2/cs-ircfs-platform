import { useI18n } from "@/i18n";

const LINKS = [
  { href: "/", label: "footer.public" },
  { href: "/report.html", label: "nav.report" },
  { href: "/app/simulator", label: "nav.simulator" },
  { href: "/docs", label: "footer.api" },
] as const;

export function AppFooter() {
  const { t } = useI18n();
  return (
    <footer className="mx-auto mt-4 max-w-[1400px] border-t border-line px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src="/app/branding/logo-96.png" alt="" width={36} height={36} className="h-9 w-9 rounded-full" />
          <div>
            <p className="text-sm font-bold text-forest">{t("footer.brand")}</p>
            <p className="text-xs text-muted">{t("footer.tagline")}</p>
          </div>
        </div>
        <nav aria-label={t("footer.brand")}>
          <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-forest">
            {LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="hover:text-primary">
                  {t(link.label)}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <p className="mt-4 text-xs text-muted">
        © {new Date().getFullYear()} {t("footer.privacy")}
      </p>
    </footer>
  );
}
