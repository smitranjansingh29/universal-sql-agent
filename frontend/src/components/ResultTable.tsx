interface Props {
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
}

export function ResultTable({ columns, rows, truncated }: Props) {
  const download = () => {
    const csv = [
      columns.join(","),
      ...rows.map((r) =>
        r
          .map((v) => {
            const s = v == null ? "" : String(v);
            return s.includes(",") || s.includes('"') || s.includes("\n")
              ? `"${s.replace(/"/g, '""')}"`
              : s;
          })
          .join(","),
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "result.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm text-gray-600">
          {rows.length} row{rows.length === 1 ? "" : "s"}
          {truncated && <span className="ml-2 text-amber-600">· truncated at 500</span>}
        </div>
        <button onClick={download} className="text-xs text-blue-700 underline">
          Download CSV
        </button>
      </div>
      <div className="overflow-x-auto border border-gray-200 rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              {columns.map((c) => (
                <th key={c} className="px-3 py-2 text-left font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-gray-100">
                {r.map((v, j) => (
                  <td key={j} className="px-3 py-1.5 font-mono text-xs">
                    {v == null ? <span className="text-gray-400">null</span> : String(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}