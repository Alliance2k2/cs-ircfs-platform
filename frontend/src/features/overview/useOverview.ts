import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";
import { apiGet, query } from "@/services/api/client";
import { executiveOverviewSchema, schemeSchema, sectorSchema } from "@/services/api/schemas";

export const PERIODS = [7, 30, 90, 365] as const;
const REFRESH_MS = 60_000;

export interface OverviewFilters {
  days: number;
  schemeId: number | null;
  sectorId: number | null;
}

const positive = (value: string | null) => {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : null;
};

/** Filters live in the address bar, so a filtered view can be bookmarked and shared. */
export function useOverviewFilters(): [OverviewFilters, (next: Partial<OverviewFilters>) => void] {
  const [params, setParams] = useSearchParams();
  const days = positive(params.get("days"));
  const filters: OverviewFilters = {
    days: days && (PERIODS as readonly number[]).includes(days) ? days : 30,
    schemeId: positive(params.get("scheme")),
    sectorId: positive(params.get("sector")),
  };
  const update = (next: Partial<OverviewFilters>) => {
    const merged = { ...filters, ...next };
    const search = new URLSearchParams();
    if (merged.days !== 30) search.set("days", String(merged.days));
    if (merged.schemeId) search.set("scheme", String(merged.schemeId));
    if (merged.sectorId) search.set("sector", String(merged.sectorId));
    setParams(search, { replace: true });
  };
  return [filters, update];
}

export function useOverview(filters: OverviewFilters) {
  return useQuery({
    queryKey: ["executive-overview", filters],
    queryFn: ({ signal }) =>
      apiGet(
        `analytics/executive-overview${query({ days: filters.days, scheme_id: filters.schemeId, sector_id: filters.sectorId })}`,
        executiveOverviewSchema,
        signal,
      ),
    placeholderData: keepPreviousData,
    refetchInterval: REFRESH_MS,
    refetchIntervalInBackground: false,
  });
}

export function useFilterOptions() {
  const schemes = useQuery({
    queryKey: ["irrigation-schemes"],
    queryFn: ({ signal }) => apiGet("irrigation-schemes", z.array(schemeSchema), signal),
    staleTime: 10 * 60_000,
  });
  const sectors = useQuery({
    queryKey: ["sectors"],
    queryFn: ({ signal }) => apiGet("sectors", z.array(sectorSchema), signal),
    staleTime: 60 * 60_000,
  });
  return { schemes: schemes.data ?? [], sectors: sectors.data ?? [] };
}
