import { ArrowUpRight, Bug, MessageSquareText, Wrench } from "lucide-react";
import { DataState } from "@/components/feedback/DataState";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/i18n";
import { formatDate, relativeTime } from "@/lib/format";
import type { PriorityAction } from "@/services/api/schemas";

const PRIORITY_TONE: Record<string, Tone> = { critical: "critical", high: "warning", medium: "neutral" };
const ICON = { infrastructure: Wrench, pest_or_disease: Bug, community_feedback: MessageSquareText } as const;

/** ``actions`` is null when the signed-in role may not see the queue. */
export function PriorityActions({ actions }: { actions: PriorityAction[] | null }) {
  const { t, lang } = useI18n();

  return (
    <Card className="flex flex-col" aria-labelledby="actions-title">
      <CardHeader
        id="actions-title"
        title={t("section.actions")}
        note={t("section.actionsNote")}
        action={
          actions && actions.length > 0 ? (
            <a href="/act-now.html" className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:text-primary-strong">
              {t("section.actionsAll")}
              <ArrowUpRight aria-hidden className="h-4 w-4" />
            </a>
          ) : undefined
        }
      />
      {actions === null ? (
        <DataState kind="empty" message={t("section.actionsStaff")} />
      ) : actions.length === 0 ? (
        <DataState kind="empty" message={t("section.actionsEmpty")} />
      ) : (
        <ol className="divide-y divide-line">
          {actions.map((action) => {
            const Icon = ICON[action.item_type as keyof typeof ICON] ?? Wrench;
            const priority = (["critical", "high", "medium"] as const).find((p) => p === action.priority);
            return (
              <li key={`${action.item_type}-${action.item_id}`} className="flex items-start gap-3 px-5 py-3.5">
                <span aria-hidden className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-control bg-canvas text-forest">
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink">{action.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {[action.sector, relativeTime(action.created_at, lang), action.assigned ? t("action.assigned") : t("action.unassigned")]
                      .filter(Boolean)
                      .join(" · ")}
                    {action.due_at && ` · ${t("action.due", { date: formatDate(action.due_at, lang) })}`}
                  </p>
                </div>
                <Badge tone={PRIORITY_TONE[action.priority] ?? "neutral"}>{priority ? t(`priority.${priority}`) : action.priority}</Badge>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
