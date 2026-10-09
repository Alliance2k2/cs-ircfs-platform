import { AlertTriangle, Inbox, Loader2, RefreshCw, WifiOff } from "lucide-react";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";

type Kind = "loading" | "empty" | "error" | "unreachable";

interface DataStateProps {
  kind: Kind;
  message?: string;
  onRetry?: () => void;
  fullPage?: boolean;
  compact?: boolean;
}

const ICONS = { loading: Loader2, empty: Inbox, error: AlertTriangle, unreachable: WifiOff };

/**
 * Every place that shows data uses this for its other states, so loading, empty, error
 * and offline always look and read the same. It never invents placeholder figures.
 */
export function DataState({ kind, message, onRetry, fullPage, compact }: DataStateProps) {
  const { t } = useI18n();
  const Icon = ICONS[kind];
  const fallback = { loading: t("state.loading"), empty: t("state.empty"), error: t("state.error"), unreachable: t("state.unreachable") }[kind];
  const problem = kind === "error" || kind === "unreachable";

  return (
    <div
      role={problem ? "alert" : "status"}
      aria-busy={kind === "loading" || undefined}
      className={cx("flex flex-col items-center justify-center gap-2 text-center", fullPage ? "min-h-screen p-8" : compact ? "px-4 py-6" : "px-6 py-10")}
    >
      <Icon aria-hidden className={cx("h-6 w-6", kind === "loading" && "animate-spin", problem ? "text-critical" : "text-muted")} />
      <p className={cx("max-w-sm text-sm", problem ? "text-ink" : "text-muted")}>{message ?? fallback}</p>
      {problem && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-1.5 rounded-control border border-line bg-surface px-3 py-1.5 text-sm font-semibold text-forest hover:bg-canvas"
        >
          <RefreshCw aria-hidden className="h-4 w-4" />
          {t("state.retry")}
        </button>
      )}
    </div>
  );
}
