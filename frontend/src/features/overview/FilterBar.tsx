import { RefreshCw } from "lucide-react";
import { Select } from "@/components/ui/Select";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatTime } from "@/lib/format";
import { PERIODS, useFilterOptions, type OverviewFilters } from "./useOverview";

interface FilterBarProps {
  filters: OverviewFilters;
  onChange: (next: Partial<OverviewFilters>) => void;
  onRefresh: () => void;
  refreshing: boolean;
  updatedAt: number;
}

export function FilterBar({ filters, onChange, onRefresh, refreshing, updatedAt }: FilterBarProps) {
  const { t, lang } = useI18n();
  const { schemes, sectors } = useFilterOptions();
  const id = (value: string) => (value ? Number(value) : null);

  return (
    <div className="flex flex-wrap items-end gap-3">
      <Select
        label={t("filter.scheme")}
        value={filters.schemeId ? String(filters.schemeId) : ""}
        onChange={(value) => onChange({ schemeId: id(value) })}
        options={[{ value: "", label: t("filter.allSchemes") }, ...schemes.filter((s) => s.is_active).map((s) => ({ value: String(s.id), label: s.name }))]}
      />
      <Select
        label={t("filter.sector")}
        value={filters.sectorId ? String(filters.sectorId) : ""}
        onChange={(value) => onChange({ sectorId: id(value) })}
        options={[{ value: "", label: t("filter.allSectors") }, ...sectors.map((s) => ({ value: String(s.id), label: s.name }))]}
      />
      <Select
        label={t("filter.period")}
        value={String(filters.days)}
        onChange={(value) => onChange({ days: Number(value) })}
        options={PERIODS.map((days) => ({ value: String(days), label: t("filter.days", { n: days }) }))}
      />
      <div className="flex flex-col items-start gap-1">
        <span className="text-2xs text-muted" aria-live="polite">
          {updatedAt ? t("filter.updated", { time: formatTime(new Date(updatedAt), lang) }) : " "}
        </span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex h-10 items-center gap-2 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-forest hover:bg-canvas disabled:opacity-60"
        >
          <RefreshCw aria-hidden className={cx("h-4 w-4", refreshing && "animate-spin")} />
          {t("filter.refresh")}
        </button>
      </div>
    </div>
  );
}
