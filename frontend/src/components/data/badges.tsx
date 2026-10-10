import { Badge, type Tone } from "@/components/ui/Badge";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";

const STATUS_TONE: Record<string, Tone> = {
  open: "critical",
  triaged: "warning",
  assigned: "warning",
  in_progress: "water",
  resolved: "good",
  closed: "neutral",
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const key = `status.${status}` as MessageKey;
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{t(key)}</Badge>;
}

const PRIORITY_TONE: Record<string, Tone> = { critical: "critical", high: "warning", medium: "water" };

export function PriorityBadge({ priority }: { priority: string }) {
  const { t } = useI18n();
  const known = priority === "critical" || priority === "high" || priority === "medium";
  return <Badge tone={PRIORITY_TONE[priority] ?? "neutral"}>{known ? t(`priority.${priority}`) : priority}</Badge>;
}

const VERIFICATION_TONE: Record<string, Tone> = { verified: "good", rejected: "critical", unverified: "neutral" };

export function VerificationBadge({ status }: { status: string }) {
  const { t } = useI18n();
  return <Badge tone={VERIFICATION_TONE[status] ?? "neutral"}>{t(`verification.${status}` as MessageKey)}</Badge>;
}

/** Only non-field data gets a badge: field reports are the normal case. */
export function OriginBadge({ origin }: { origin: string }) {
  const { t } = useI18n();
  if (origin === "field") return null;
  const label = origin === "demo" ? t("origin.demo") : origin === "import" ? t("origin.import") : origin;
  return <Badge tone={origin === "demo" ? "warning" : "water"}>{label}</Badge>;
}

export function FlagBadges({ flags }: { flags: string[] }) {
  const { t } = useI18n();
  if (!flags.length) return <span className="text-xs text-muted">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {flags.map((flag) => (
        <Badge key={flag} tone={flag === "unusual_value" || flag === "possible_duplicate" ? "warning" : "neutral"}>
          {t(`flag.${flag}` as MessageKey)}
        </Badge>
      ))}
    </span>
  );
}

/** A label and value pair inside a detail drawer. */
export function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[8.5rem_1fr] gap-3 border-b border-line/70 py-2 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-ink">{children}</dd>
    </div>
  );
}
