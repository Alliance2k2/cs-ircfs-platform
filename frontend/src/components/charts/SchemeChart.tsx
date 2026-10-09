import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { tokenColor } from "@/lib/tokens";

export type ChartRow = { name: string } & Record<string, string | number>;

interface SchemeChartProps {
  data: ChartRow[];
  series: { key: string; color: string }[];
  caption: string;
  schemeLabel: string;
}

/** Grouped bars per scheme, with the same figures as a visually hidden table for screen readers. */
export default function SchemeChart({ data, series, caption, schemeLabel }: SchemeChartProps) {
  return (
    <figure>
      <figcaption className="sr-only">{caption}</figcaption>
      <div className="h-56" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -18 }} barGap={3}>
            <CartesianGrid vertical={false} stroke={tokenColor("line")} />
            <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: tokenColor("muted"), fontSize: 12 }} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: tokenColor("muted"), fontSize: 12 }} />
            <Tooltip cursor={{ fill: tokenColor("mint", 0.5) }} contentStyle={{ borderRadius: 10, borderColor: tokenColor("line"), fontSize: 12 }} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
            {series.map((item) => (
              <Bar key={item.key} dataKey={item.key} fill={item.color} radius={[4, 4, 0, 0]} maxBarSize={28} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <thead>
          <tr>
            <th scope="col">{schemeLabel}</th>
            {series.map((item) => (
              <th key={item.key} scope="col">
                {item.key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.name}>
              <th scope="row">{row.name}</th>
              {series.map((item) => (
                <td key={item.key}>{row[item.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
