import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { DataState } from "@/components/feedback/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** A value to sort by; columns without one are not sortable. */
  sortValue?: (row: T) => string | number | null;
  className?: string;
  /** Shown as the card title on phones. */
  primary?: boolean;
}

interface DataTableProps<T> {
  rows: T[] | undefined;
  columns: Column<T>[];
  rowKey: (row: T) => string | number;
  caption: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  emptyMessage: string;
  /** Text searched by the search box; omit to hide the search box. */
  searchText?: (row: T) => string;
  onRowClick?: (row: T) => void;
  toolbar?: ReactNode;
  pageSize?: number;
  initialSort?: { key: string; direction: "asc" | "desc" };
}

/**
 * Search, sort and pages for any list of records. A table on wide screens and stacked
 * cards on phones, so nothing scrolls sideways.
 */
export function DataTable<T>({
  rows, columns, rowKey, caption, loading, error, onRetry, emptyMessage, searchText, onRowClick, toolbar, pageSize = 15, initialSort,
}: DataTableProps<T>) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState(initialSort ?? null);
  const [page, setPage] = useState(0);

  const shown = useMemo(() => {
    let list = rows ?? [];
    const needle = query.trim().toLowerCase();
    if (needle && searchText) list = list.filter((row) => searchText(row).toLowerCase().includes(needle));
    const column = sort && columns.find((item) => item.key === sort.key);
    if (column?.sortValue) {
      const direction = sort!.direction === "asc" ? 1 : -1;
      list = [...list].sort((a, b) => {
        const [x, y] = [column.sortValue!(a), column.sortValue!(b)];
        if (x === y) return 0;
        if (x === null) return 1;
        if (y === null) return -1;
        return (x < y ? -1 : 1) * direction;
      });
    }
    return list;
  }, [rows, query, sort, columns, searchText]);

  const pages = Math.max(1, Math.ceil(shown.length / pageSize));
  const current = Math.min(page, pages - 1);
  const visible = shown.slice(current * pageSize, current * pageSize + pageSize);
  const toggleSort = (key: string) => {
    setSort((value) => (value?.key === key ? { key, direction: value.direction === "asc" ? "desc" : "asc" } : { key, direction: "desc" }));
    setPage(0);
  };

  return (
    <div className="rounded-card border border-line bg-surface shadow-card">
      {(searchText || toolbar) && (
        <div className="flex flex-wrap items-end gap-3 border-b border-line px-4 py-3">
          {searchText && (
            <label className="relative min-w-[12rem] flex-1">
              <span className="sr-only">{t("table.search")}</span>
              <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                type="search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(0);
                }}
                placeholder={t("table.search")}
                className="h-10 w-full rounded-control border border-line bg-surface pl-9 pr-3 text-sm"
              />
            </label>
          )}
          {toolbar}
        </div>
      )}

      {loading && !rows ? (
        <div className="space-y-2 p-4" aria-busy>
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      ) : error && !rows ? (
        <DataState kind="error" message={error} onRetry={onRetry} />
      ) : shown.length === 0 ? (
        <DataState kind="empty" message={query ? t("table.noMatch") : emptyMessage} />
      ) : (
        <>
          <table className="hidden w-full text-sm md:table">
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr className="border-b border-line text-left text-2xs font-bold uppercase tracking-wider text-muted">
                {columns.map((column) => (
                  <th key={column.key} scope="col" className={cx("px-4 py-2.5", column.className)}
                      aria-sort={sort?.key === column.key ? (sort.direction === "asc" ? "ascending" : "descending") : undefined}>
                    {column.sortValue ? (
                      <button type="button" onClick={() => toggleSort(column.key)} className="inline-flex items-center gap-1 uppercase hover:text-forest">
                        {column.header}
                        {sort?.key === column.key && (sort.direction === "asc" ? <ArrowUp aria-hidden className="h-3 w-3" /> : <ArrowDown aria-hidden className="h-3 w-3" />)}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr
                  key={rowKey(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cx("border-b border-line last:border-0", onRowClick && "cursor-pointer hover:bg-canvas")}
                >
                  {columns.map((column, index) => (
                    <td key={column.key} className={cx("px-4 py-3 align-top", column.className)}>
                      {index === 0 && onRowClick ? (
                        <button type="button" onClick={(event) => { event.stopPropagation(); onRowClick(row); }} className="text-left font-semibold text-forest hover:underline">
                          {column.render(row)}
                        </button>
                      ) : (
                        column.render(row)
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <ul className="divide-y divide-line md:hidden" aria-label={caption}>
            {visible.map((row) => {
              const primary = columns.find((column) => column.primary) ?? columns[0]!;
              return (
                <li key={rowKey(row)}>
                  <button
                    type="button"
                    disabled={!onRowClick}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className="block w-full px-4 py-3 text-left enabled:hover:bg-canvas"
                  >
                    <span className="block text-sm font-semibold text-forest">{primary.render(row)}</span>
                    <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                      {columns.filter((column) => column !== primary).map((column) => (
                        <div key={column.key} className="min-w-0">
                          <dt className="text-muted">{column.header}</dt>
                          <dd className="truncate text-ink">{column.render(row)}</dd>
                        </div>
                      ))}
                    </dl>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-2.5 text-xs text-muted">
            <span>{t("table.count", { shown: visible.length, total: shown.length })}</span>
            {pages > 1 && (
              <div className="flex items-center gap-1">
                <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)} className="rounded p-1.5 hover:bg-canvas disabled:opacity-40">
                  <ChevronLeft aria-hidden className="h-4 w-4" />
                  <span className="sr-only">{t("table.previous")}</span>
                </button>
                <span>{t("table.page", { page: current + 1, pages })}</span>
                <button type="button" disabled={current >= pages - 1} onClick={() => setPage(current + 1)} className="rounded p-1.5 hover:bg-canvas disabled:opacity-40">
                  <ChevronRight aria-hidden className="h-4 w-4" />
                  <span className="sr-only">{t("table.next")}</span>
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
