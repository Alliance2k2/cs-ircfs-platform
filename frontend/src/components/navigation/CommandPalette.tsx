import { CornerDownLeft, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { canAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { Dialog } from "@/components/ui/Overlay";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { ROUTES } from "./nav";

/** Jump to any page by typing part of its name (Ctrl+K or the search button). */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const { role } = useSession();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return ROUTES.filter((route) => canAccess(role, route.access)).filter(
      (route) => !needle || `${t(route.label)} ${t(route.group)}`.toLowerCase().includes(needle),
    );
  }, [query, role, t]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setIndex(0);
      window.setTimeout(() => input.current?.focus(), 0);
    }
  }, [open]);

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  return (
    <Dialog open={open} onClose={onClose} title={t("shell.search")} actions={null}>
      <label className="relative block">
        <span className="sr-only">{t("shell.searchHint")}</span>
        <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          ref={input}
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-results"
          aria-activedescendant={matches[index] ? `palette-${matches[index]!.to}` : undefined}
          value={query}
          placeholder={t("shell.searchHint")}
          onChange={(event) => {
            setQuery(event.target.value);
            setIndex(0);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setIndex((value) => Math.min(value + 1, matches.length - 1));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setIndex((value) => Math.max(value - 1, 0));
            } else if (event.key === "Enter" && matches[index]?.to) {
              go(matches[index]!.to!);
            }
          }}
          className="h-11 w-full rounded-control border border-line bg-surface pl-9 pr-3 text-sm"
        />
      </label>
      <ul id="palette-results" role="listbox" className="mt-3 max-h-80 overflow-y-auto">
        {matches.length === 0 && <li className="px-3 py-4 text-sm text-muted">{t("shell.noPages")}</li>}
        {matches.map((route, position) => {
          const Icon = route.icon;
          return (
            <li key={route.to} id={`palette-${route.to}`} role="option" aria-selected={position === index}>
              <button
                type="button"
                onClick={() => go(route.to!)}
                onMouseEnter={() => setIndex(position)}
                className={cx("flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left text-sm", position === index ? "bg-mint text-forest" : "text-ink")}
              >
                <Icon aria-hidden className="h-4 w-4 shrink-0 text-primary" />
                <span className="flex-1">
                  <span className="font-semibold">{t(route.label)}</span>
                  <span className="ml-2 text-xs text-muted">{t(route.group)}</span>
                </span>
                {position === index && <CornerDownLeft aria-hidden className="h-4 w-4 text-muted" />}
              </button>
            </li>
          );
        })}
      </ul>
    </Dialog>
  );
}
