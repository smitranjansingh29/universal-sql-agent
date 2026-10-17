import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useConnection } from "../context/useConnection";
import type { TableInfo } from "../api/types";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

interface SchemaResponse {
  tables: TableInfo[];
  dialect: string;
  date_column: string | null;
}

export function Schema() {
  const { active } = useConnection();
  const navigate = useNavigate();
  const [data, setData] = useState<SchemaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  
  // New state for RAG indexing
  const [indexing, setIndexing] = useState(false);
  const [indexMsg, setIndexMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;

    fetch(`${API}/api/connections/${active.id}/schema`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: SchemaResponse) => {
        if (cancelled) return;
        setData(d);
        setError(null);
        setExpanded(d.tables[0]?.name ?? null);
      })
      .catch((e) => {
        if (cancelled) return;
        setData(null);
        setError(e.message);
      });

    return () => {
      cancelled = true;
    };
  }, [active]);

  // New function to trigger indexing
  const handleReindex = async () => {
    if (!active) return;
    setIndexing(true);
    setIndexMsg(null);
    try {
      const r = await fetch(`${API}/api/connections/${active.id}/index`, { method: "POST" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setIndexMsg("Indexing started in the background. Please wait 20-30 seconds, then ask a question.");
    } catch (e) {
      setIndexMsg(`Indexing failed: ${(e as Error).message}`);
    } finally {
      setIndexing(false);
    }
  };

  if (!active) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-600 mb-4">No connection selected.</p>
        <button
          onClick={() => navigate("/connect")}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          Go to Connect
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-6">
      <div className="col-span-2 bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">
            Schema — {active.name}{" "}
            <span className="text-sm text-gray-500">({data?.dialect ?? "…"})</span>
          </h2>
          
          {/* Added Reindex Button */}
          <div className="flex gap-2">
            <button
              onClick={handleReindex}
              disabled={indexing}
              className="bg-amber-600 hover:bg-amber-700 text-white px-3 py-2 rounded text-sm font-medium"
            >
              {indexing ? "Indexing…" : "Reindex for RAG"}
            </button>
            <button
              onClick={() => navigate("/ask")}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium"
            >
              Go to Ask →
            </button>
          </div>
        </div>

        {indexMsg && (
          <div className="mb-4 text-sm bg-blue-50 border border-blue-200 text-blue-800 px-3 py-2 rounded">
            {indexMsg}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-3 py-2 rounded text-sm mb-4">
            {error}
          </div>
        )}

        {!data && !error && <p className="text-gray-500">Loading schema…</p>}

        {data && (
          <div className="space-y-2">
            {data.tables.map((t) => {
              const isOpen = expanded === t.name;
              return (
                <div key={t.name} className="border border-gray-200 rounded">
                  <button
                    onClick={() => setExpanded(isOpen ? null : t.name)}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between"
                  >
                    <span>
                      <span className="font-mono font-medium">{t.name}</span>{" "}
                      <span className="text-xs text-gray-500">
                        ({t.columns.length} columns)
                      </span>
                    </span>
                    <span className="text-xs text-gray-500">
                      {isOpen ? "▾" : "▸"}
                    </span>
                  </button>
                  {isOpen && (
                    <div className="px-3 py-2 border-t border-gray-100 bg-gray-50 text-sm">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-left text-gray-500">
                            <th className="py-1">Column</th>
                            <th>Type</th>
                            <th>Nullable</th>
                            <th>PK</th>
                          </tr>
                        </thead>
                        <tbody>
                          {t.columns.map((c) => (
                            <tr key={c.name} className="border-t border-gray-100">
                              <td className="py-1 font-mono">{c.name}</td>
                              <td className="text-gray-600">{c.type}</td>
                              <td className="text-gray-600">{c.nullable ? "yes" : "no"}</td>
                              <td>{t.pk.includes(c.name) ? "🔑" : ""}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {t.fks.length > 0 && (
                        <div className="mt-2 text-xs text-gray-600">
                          <span className="font-medium">Foreign keys:</span>
                          {t.fks.map((fk, i) => (
                            <div key={i} className="font-mono">
                              {fk.cols.join(", ")} → {fk.ref_table}.{fk.ref_cols.join(", ")}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200 h-fit">
        <h3 className="font-semibold mb-2">RAG (Phase 2)</h3>
        <ul className="text-sm text-gray-700 space-y-2 list-disc pl-5">
          <li><strong>Database migrated:</strong> You are now connected to Neon Postgres.</li>
          <li><strong>Indexing:</strong> Clicking "Reindex" asks GPT to write descriptions for tables and saves them as embeddings in Neon.</li>
          <li><strong>Retrieval:</strong> If a database has &gt; 15 tables, the system will automatically search the embeddings to find the right tables before writing SQL.</li>
        </ul>
      </div>
    </div>
  );
}