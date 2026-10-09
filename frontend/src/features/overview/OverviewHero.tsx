import { Map as MapIcon, MapPin, Radio, Zap } from "lucide-react";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatNumber } from "@/lib/format";
import type { ExecutiveOverview } from "@/services/api/schemas";

// Same field photograph as the classic dashboard; the gradient alone remains if it cannot load.
const PHOTO = "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1800&q=70";

function greetingKey(now = new Date()): MessageKey {
  const hour = Number(new Intl.DateTimeFormat("en-GB", { hour: "numeric", hourCycle: "h23", timeZone: "Africa/Kigali" }).format(now));
  return hour < 12 ? "greet.morning" : hour < 17 ? "greet.afternoon" : "greet.evening";
}

const STATS: { key: string; label: MessageKey }[] = [
  { key: "citizen_reports", label: "hero.stat.reports" },
  { key: "open_actions", label: "hero.stat.actions" },
  { key: "critical_incidents", label: "hero.stat.critical" },
  { key: "active_reporters", label: "hero.stat.reporters" },
];

/** The welcome banner: who you are, today's four headline numbers, and the two most used next steps. */
export function OverviewHero({ data }: { data: ExecutiveOverview | undefined }) {
  const { t, lang } = useI18n();
  const { account, role } = useSession();
  const firstName = account?.full_name?.split(/\s+/)[0] || t("greet.planner");
  const values = new Map(data?.metrics.map((metric) => [metric.key, metric.value]));

  return (
    <header
      className="relative isolate overflow-hidden rounded-[24px] bg-forest px-5 py-7 text-white shadow-raised sm:px-9 sm:py-8"
      style={{
        backgroundImage: `linear-gradient(100deg, rgb(3 36 24 / 0.97) 0%, rgb(4 52 35 / 0.9) 42%, rgb(7 74 48 / 0.6) 100%), url("${PHOTO}")`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* Faint contour lines, like field rows */}
      <div
        aria-hidden
        className="absolute inset-0 -z-10 opacity-70"
        style={{ backgroundImage: "repeating-radial-gradient(ellipse at 88% 110%, transparent 0 46px, rgb(234 248 203 / 0.05) 47px 48px, transparent 49px 90px)" }}
      />
      <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0">
          <p className="text-2xs font-bold uppercase tracking-[0.18em] text-lime">{t("hero.eyebrow")}</p>
          <h1 className="mt-2 font-heading text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            {t(greetingKey())}, {firstName}
          </h1>
          <p className="mt-2 max-w-xl text-sm text-white/75 sm:text-base">{t("hero.subtitle")}</p>

          <ul className="mt-6 grid max-w-3xl grid-cols-2 gap-3 md:grid-cols-4">
            {STATS.map((stat) => {
              const value = values.get(stat.key);
              return (
                <li key={stat.key} className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
                  <span className="tabular block font-heading text-2xl font-extrabold text-lime">
                    {value === undefined ? "–" : value === null ? "—" : formatNumber(value, lang)}
                  </span>
                  <span className="text-xs font-semibold text-white/80">{t(stat.label)}</span>
                </li>
              );
            })}
          </ul>

          <div className="mt-6 flex flex-wrap gap-3">
            {isStaff(role) && (
              <a
                href="/act-now.html"
                className="inline-flex items-center gap-2 rounded-xl bg-lime px-4 py-2.5 text-sm font-bold text-forest shadow-[0_10px_26px_rgb(var(--lime)/0.25)] hover:brightness-95"
              >
                <Zap aria-hidden className="h-4 w-4" />
                {t("hero.openActNow")}
              </a>
            )}
            <a href="/map.html" className="inline-flex items-center gap-2 rounded-xl border border-white/35 px-4 py-2.5 text-sm font-bold text-white hover:bg-white/10">
              <MapIcon aria-hidden className="h-4 w-4" />
              {t("hero.map")}
            </a>
          </div>
        </div>

        <div aria-hidden className="relative hidden h-56 w-56 place-items-center lg:grid">
          <span className="absolute inset-0 rounded-full border border-white/15" />
          <span className="absolute inset-4 rounded-full border border-dashed border-white/20" />
          <img src="/app/branding/logo-192.png" alt="" width={184} height={184} className="relative h-[184px] w-[184px] rounded-full border-[6px] border-white/90 bg-white shadow-[0_20px_50px_rgb(0_20_12/0.45)]" />
          <span className="absolute -top-1 right-0 inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-2xs font-bold text-forest shadow-raised">
            <Radio className="h-3.5 w-3.5" />
            {t("hero.channels")}
          </span>
          <span className="absolute -bottom-1 -right-2 inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-2xs font-bold text-forest shadow-raised">
            <MapPin className="h-3.5 w-3.5" />
            {t("hero.district")}
          </span>
        </div>
      </div>
    </header>
  );
}
