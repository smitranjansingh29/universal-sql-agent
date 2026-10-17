import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

interface Props {
  chart: "bar" | "line" | "pie" | "table";
  columns: string[];
  rows: unknown[][];
  x?: string | null;
  y?: string[] | null;
}

const COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"];

export function ResultChart({ chart, columns, rows }: Props) {
  if (chart === "table" || rows.length === 0) return null;
  if (columns.length < 2) return null;

  // Build data: first column is X (or label), remaining numeric columns are series
  const xKey = columns[0];
  const yKeys = columns.slice(1).filter((_, idx) => {
    return rows.some((r) => typeof r[idx + 1] === "number");
  });

  if (yKeys.length === 0) return null;

  const data = rows.slice(0, 50).map((r) => {
    const obj: Record<string, unknown> = { [xKey]: r[0] };
    yKeys.forEach((k, i) => {
      obj[k] = r[i + 1];
    });
    return obj;
  });

  const render = () => {
    if (chart === "line") {
      return (
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          {yKeys.map((k) => (
            <Line key={k} type="monotone" dataKey={k} stroke="#2563eb" />
          ))}
        </LineChart>
      );
    }
    if (chart === "pie" && yKeys[0]) {
      return (
        <PieChart>
          <Tooltip />
          <Pie data={data} dataKey={yKeys[0]} nameKey={xKey} outerRadius={100} label>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      );
    }
    return (
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={xKey} />
        <YAxis />
        <Tooltip />
        {yKeys.map((k) => (
          <Bar key={k} dataKey={k} fill="#2563eb" />
        ))}
      </BarChart>
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded p-4">
      <div className="text-sm font-medium mb-2 text-gray-700">Chart ({chart})</div>
      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>{render()}</ResponsiveContainer>
      </div>
    </div>
  );
}