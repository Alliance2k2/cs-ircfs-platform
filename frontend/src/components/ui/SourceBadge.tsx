import { CircleDashed, FileCheck2, FlaskConical, Radio, ShieldCheck } from "lucide-react";
import { useI18n } from "@/i18n";
import type { MetricSource } from "@/services/api/schemas";
import { Badge, type Tone } from "./Badge";

const STYLE: Record<MetricSource, { tone: Tone; Icon: typeof Radio }> = {
  live_unverified: { tone: "water", Icon: Radio },
  platform: { tone: "good", Icon: ShieldCheck },
  documented: { tone: "good", Icon: FileCheck2 },
  demo: { tone: "warning", Icon: FlaskConical },
  missing: { tone: "neutral", Icon: CircleDashed },
};

/** How far a figure can be trusted, in words and colour (never colour alone). */
export function SourceBadge({ source }: { source: MetricSource }) {
  const { t } = useI18n();
  const { tone, Icon } = STYLE[source];
  return (
    <Badge tone={tone}>
      <Icon aria-hidden className="h-3 w-3" />
      {t(`source.${source}`)}
    </Badge>
  );
}
