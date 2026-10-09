import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CloudRain,
  HeartPulse,
  type LucideIcon,
  MapPin,
  MessageSquareText,
  TrendingUp,
} from "lucide-react";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import type { Accent } from "@/components/ui/MetricCard";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { cx } from "@/lib/cx";
import { formatNumber } from "@/lib/format";
import type { ExecutiveOverview } from "@/services/api/schemas";

interface Module {
  href: string;
  title: MessageKey;
  description: MessageKey;
  icon: LucideIcon;
  accent: Accent;
  count?: (data: ExecutiveOverview) => { value: string; label: MessageKey } | null;
  staffOnly?: boolean;
}

const metricValue = (data: ExecutiveOverview, key: string) => data.metrics.find((metric) => metric.key === key)?.value ?? null;

const MODULES: Module[] = [
  {
    href: "/act-now.html", title: "nav.actnow", description: "module.actnow", icon: AlertTriangle, accent: "coral", staffOnly: true,
    count: (d) => ({ value: String(d.counts.open_cases + d.counts.open_grievances), label: "module.count.openItems" }),
  },
  {
    href: "/channels.html", title: "nav.channels", description: "module.channels", icon: Activity, accent: "blue",
    count: (d) => {
      const value = metricValue(d, "citizen_reports");
      return value === null ? null : { value: String(value), label: "module.count.reports" };
    },
  },
  {
    href: "/schemes.html", title: "nav.schemes", description: "module.schemes", icon: BarChart3, accent: "green",
    count: (d) => ({ value: String(d.schemes.length), label: "module.count.schemes" }),
  },
  { href: "/trends.html", title: "nav.trends", description: "module.trends", icon: TrendingUp, accent: "teal", count: () => ({ value: "12", label: "module.count.months" }) },
  {
    href: "/advice.html", title: "nav.advice", description: "module.advice", icon: CloudRain, accent: "gold",
    count: (d) => ({ value: String(d.counts.sectors_with_rain), label: "module.count.rainSectors" }),
  },
  { href: "/nutrition.html", title: "nav.food", description: "module.food", icon: HeartPulse, accent: "violet" },
  {
    href: "/map.html", title: "nav.map", description: "module.map", icon: MapPin, accent: "green",
    count: (d) => ({ value: `${d.counts.sectors_reporting} / ${d.counts.sectors_total}`, label: "module.count.sectors" }),
  },
  {
    href: "/feedback.html", title: "nav.feedback", description: "module.feedback", icon: MessageSquareText, accent: "coral",
    count: (d) => ({ value: String(d.counts.open_grievances), label: "module.count.grievances" }),
  },
];

const COUNT_COLOUR: Record<Accent, string> = {
  green: "text-primary", blue: "text-water", gold: "text-amber", coral: "text-critical", violet: "text-violet", teal: "text-teal",
};
const SOFT: Record<Accent, string> = {
  green: "bg-mint text-primary", blue: "bg-water-soft text-water", gold: "bg-amber-soft text-amber",
  coral: "bg-critical-soft text-critical", violet: "bg-violet-soft text-violet", teal: "bg-teal-soft text-teal",
};

/** Shortcuts to every workspace, each with one live count. Classic pages until they are rebuilt. */
export function ModuleGrid({ data }: { data: ExecutiveOverview }) {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const modules = MODULES.filter((module) => !module.staffOnly || isStaff(role));

  return (
    <section aria-labelledby="modules-title">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-2xs font-bold uppercase tracking-[0.16em] text-primary">{t("modules.eyebrow")}</p>
          <h2 id="modules-title" className="mt-1 text-xl font-extrabold">
            {t("modules.title")}
          </h2>
        </div>
        <p className="text-sm text-muted">{t("modules.note")}</p>
      </div>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {modules.map((module) => {
          const Icon = module.icon;
          const count = module.count?.(data) ?? null;
          return (
            <li key={module.href}>
              <a
                href={module.href}
                className="group flex h-full min-h-[11rem] flex-col rounded-[20px] border border-line bg-surface p-5 shadow-card transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-raised"
              >
                <div className="flex items-start gap-3.5">
                  <span aria-hidden className={cx("grid h-11 w-11 shrink-0 place-items-center rounded-[14px]", SOFT[module.accent])}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-heading text-base font-bold text-forest">{t(module.title)}</span>
                    <span className="mt-0.5 block text-sm text-muted">{t(module.description)}</span>
                  </span>
                  <ArrowUpRight aria-hidden className="h-4 w-4 shrink-0 text-muted transition group-hover:text-primary" />
                </div>
                <span className="mt-auto pt-4">
                  {count ? (
                    <>
                      <span className={cx("tabular block font-heading text-2xl font-extrabold", COUNT_COLOUR[module.accent])}>
                        {/^\d+$/.test(count.value) ? formatNumber(Number(count.value), lang) : count.value}
                      </span>
                      <span className="text-xs text-muted">{t(count.label)}</span>
                    </>
                  ) : (
                    <span className="text-sm font-semibold text-primary">{t("module.count.none")} →</span>
                  )}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
