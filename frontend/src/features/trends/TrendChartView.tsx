import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { tokenColor } from "@/lib/tokens";
import type { TrendMonth } from "@/services/api/workspaces";

export interface TrendSeries {
  key: keyof TrendMonth;
  label: string;
  /** A design token name: primary, water, amber, critical, fresh, forest. */
  color: string;
  kind: "bar" | "line";
}

/** Twelve months as bars and lines, with the same figures in a hidden table for screen readers. */
export default function TrendChartView({ months, series, caption, monthLabel }: { months: TrendMonth[]; series: TrendSeries[]; caption: string; monthLabel: string }) {
  const lines = series.filter((item) => item.kind === "line");
  const twoAxes = lines.length > 0 && series.some((item) => item.kind === "bar");
  return (
    <figure>
      <figcaption className="sr-only">{caption}</figcaption>
      <div className="h-64" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={months} margin={{ top: 4, right: twoAxes ? -10 : 4, bottom: 0, left: -18 }}>
            <CartesianGrid vertical={false} stroke={tokenColor("line")} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: tokenColor("muted"), fontSize: 11 }} tickFormatter={(value: string) => value.slice(0, 3)} />
            <YAxis yAxisId="left" allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: tokenColor("muted"), fontSize: 11 }} />
            {twoAxes && <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} tick={{ fill: tokenColor("muted"), fontSize: 11 }} />}
            <Tooltip cursor={{ fill: tokenColor("mint", 0.5) }} contentStyle={{ borderRadius: 10, borderColor: tokenColor("line"), fontSize: 12 }} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
            {series.map((item) =>
              item.kind === "bar" ? (
                <Bar key={item.key} yAxisId="left" dataKey={item.key} name={item.label} fill={tokenColor(item.color)} radius={[4, 4, 0, 0]} maxBarSize={22} />
              ) : (
                <Line key={item.key} yAxisId={twoAxes ? "right" : "left"} dataKey={item.key} name={item.label} stroke={tokenColor(item.color)} strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
              ),
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {/* Tables ignore sr-only's 1px width, so the wrapper clips it instead. */}
      <div className="sr-only">
        <table>
          <thead>
            <tr>
              <th scope="col">{monthLabel}</th>
              {series.map((item) => <th key={item.key} scope="col">{item.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {months.map((month) => (
              <tr key={month.month}>
                <th scope="row">{month.label}</th>
                {series.map((item) => <td key={item.key}>{month[item.key] ?? "—"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
