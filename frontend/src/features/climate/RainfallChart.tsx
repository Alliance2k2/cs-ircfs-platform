import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function RainfallChart({ daily }: { daily: { date: string; mean_mm: number | null }[] }) {
  return <div className="h-56" aria-hidden="true"><ResponsiveContainer width="100%" height="100%">
    <LineChart data={daily}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" tickFormatter={(d: string) => d.slice(5)} />
      <YAxis unit=" mm" /><Tooltip /><Line dataKey="mean_mm" name="Rainfall (mm)" stroke="currentColor" connectNulls={false} isAnimationActive={false} />
    </LineChart>
  </ResponsiveContainer></div>;
}
