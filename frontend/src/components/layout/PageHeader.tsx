import type { ReactNode } from "react";
import { useI18n } from "@/i18n";
import { formatTime } from "@/lib/format";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  /** When the data on the page was last fetched (ms since epoch). */
  updatedAt?: number;
}

/** Where you are and what this page is for, the same on every workspace. */
export function PageHeader({ eyebrow, title, description, actions, updatedAt }: PageHeaderProps) {
  const { t, lang } = useI18n();
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="max-w-3xl">
        <p className="text-2xs font-bold uppercase tracking-[0.16em] text-primary">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-extrabold sm:text-[1.75rem]">{title}</h1>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {updatedAt ? (
          <span className="text-2xs text-muted" aria-live="polite">
            {t("filter.updated", { time: formatTime(new Date(updatedAt), lang) })}
          </span>
        ) : null}
        {actions}
      </div>
    </header>
  );
}
