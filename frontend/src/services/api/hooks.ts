import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiGet } from "./client";
import { schemeSchema, sectorSchema } from "./schemas";
import { cellSchema } from "./workspaces";

/** GET a path with a schema, cached under the path itself. */
export function useApi<T>(path: string | null, schema: z.ZodType<T, z.ZodTypeDef, unknown>, options: Partial<UseQueryOptions<T>> = {}) {
  return useQuery<T>({
    queryKey: ["api", path],
    queryFn: ({ signal }) => apiGet(path as string, schema, signal),
    enabled: path !== null,
    ...options,
  });
}

/** Sectors, schemes and cells for filters and labels; they rarely change. */
export function useReferenceData() {
  const sectors = useApi("sectors", z.array(sectorSchema), { staleTime: 60 * 60_000 });
  const schemes = useApi("irrigation-schemes", z.array(schemeSchema), { staleTime: 10 * 60_000 });
  const cells = useApi("cells", z.array(cellSchema), { staleTime: 60 * 60_000 });
  const sectorName = new Map((sectors.data ?? []).map((sector) => [sector.id, sector.name]));
  const cellRow = new Map((cells.data ?? []).map((cell) => [cell.id, cell]));
  return {
    sectors: sectors.data ?? [],
    schemes: schemes.data ?? [],
    schemeName: new Map((schemes.data ?? []).map((scheme) => [scheme.id, scheme.name])),
    sectorName,
    /** "Sector · Cell" for a cell id, or null. */
    place: (cellId: number | null | undefined) => {
      const cell = cellId ? cellRow.get(cellId) : undefined;
      return cell ? `${sectorName.get(cell.sector_id) ?? ""} · ${cell.name}` : null;
    },
  };
}

/** Build a query string, skipping empty values. */
export function withParams(path: string, params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `${path}?${text}` : path;
}
