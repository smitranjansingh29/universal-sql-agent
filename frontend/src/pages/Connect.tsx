import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useConnection } from "../context/useConnection";
import type { Connection } from "../api/types";

const EXAMPLES = [
  { label: "Test SQLite", url: "sqlite:///./test.db" },
  { label: "Northwind", url: "sqlite:///./northwind.db" },
  { label: "Postgres (Neon)", url: "postgresql+psycopg://user:pass@host/db" },
  { label: "MySQL", url: "mysql+pymysql://user:pass@host/db" },
];

export function Connect() {
  const { active, setActive } = useConnection();
  const navigate = useNavigate();
  const [name, setName] = useState("My database");
  const [url, setUrl] = useState("sqlite:///./northwind.db");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Connection | null>(null);
  const [list, setList] = useState<Array<{ id: number; name: string; dialect: string }>>([]);

  // Load saved connections once on mount (setState only in async callback)
  useEffect(() => {
    let cancelled = false;
    api
      .listConnections()
      .then((items) => {
        if (!cancelled) setList(items);
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const conn = await api.createConnection(name, url);
      setResult(conn);
      // Refresh the saved list after creating
      try {
        const items = await api.listConnections();
        setList(items);
      } catch {
        /* non-fatal */
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">Connect a database</h2>

        <label className="block text-sm font-medium mb-1">Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 mb-4"
        />

        <label className="block text-sm font-medium mb-1">Connection URL</label>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 mb-2 font-mono text-sm"
        />
        <p className="text-xs text-gray-500 mb-4">
          Use a read-only credential. URLs are encrypted at rest.
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              onClick={() => setUrl(ex.url)}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
            >
              {ex.label}
            </button>
          ))}
        </div>

        <button
          onClick={submit}
          disabled={busy || !url}
          className="bg-blue-600 text-white px-4 py-2 rounded font-medium"
        >
          {busy ? "Testing & indexing…" : "Test & save"}
        </button>

        {error && (
          <div className="mt-4 text-sm bg-red-50 border border-red-200 text-red-800 px-3 py-2 rounded">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-4 text-sm bg-green-50 border border-green-200 text-green-900 px-3 py-2 rounded">
            ✓ Connection saved (id={result.id}). {result.tables?.length ?? 0} tables found.
            {result.warning && (
              <div className="mt-2 text-amber-800 text-xs">{result.warning}</div>
            )}
            <button
              onClick={() => {
                setActive({ id: result.id, name: result.name, dialect: result.dialect });
                navigate("/schema");
              }}
              className="mt-2 text-blue-700 underline"
            >
              Use this connection →
            </button>
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">Saved connections</h2>
        {list.length === 0 && <p className="text-gray-500 text-sm">No connections yet.</p>}
        <ul className="space-y-2">
          {list.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between border border-gray-200 rounded px-3 py-2"
            >
              <div>
                <span className="font-medium">{c.name}</span>{" "}
                <span className="text-xs text-gray-500">({c.dialect})</span>
              </div>
              <button
                onClick={() => {
                  setActive(c);
                  navigate("/ask");
                }}
                className={`text-sm px-3 py-1 rounded ${
                  active?.id === c.id
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 hover:bg-gray-200"
                }`}
              >
                {active?.id === c.id ? "Active" : "Set active"}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}