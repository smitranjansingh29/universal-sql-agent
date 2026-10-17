import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useConnection } from "../context/useConnection";
import { api } from "../api/client";
import type { QueryResponse } from "../api/types";
import { ResultTable } from "../components/ResultTable";
import { ResultChart } from "../components/ResultChart";

const STAGES = ["Finding tables…", "Writing SQL…", "Running…"];

export function Ask() {
  const { active } = useConnection();
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sqlOpen, setSqlOpen] = useState(false);

  // Advance stage over time — setState is only inside timer callbacks, which is allowed
  useEffect(() => {
    if (!busy) return;
    const t1 = setTimeout(() => setStage(1), 800);
    const t2 = setTimeout(() => setStage(2), 1800);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [busy]);

  const submit = async () => {
    if (!active || !question.trim()) return;
    setStage(0);              // reset here, not in the effect
    setBusy(true);
    setError(null);
    setResult(null);
    setSqlOpen(false);
    try {
      const r = await api.ask(active.id, question.trim());
      setResult(r);
      if (r.error) setError(`${r.error}: ${r.detail ?? ""}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!active) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-600 mb-4">Select a connection first.</p>
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
    <div className="max-w-4xl mx-auto">
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-3">
          Ask a question — {active.name}
        </h2>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={3}
          placeholder="e.g. Which 5 customers have spent the most money in total?"
          className="w-full border border-gray-300 rounded px-3 py-2 mb-3 font-sans"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={submit}
            disabled={busy || !question.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded font-medium"
          >
            {busy ? "Thinking…" : "Ask"}
          </button>
          {busy && <span className="text-sm text-gray-600">{STAGES[stage]}</span>}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {result && !result.error && (
        <div className="space-y-4">
          {result.summary && (
            <div className="bg-blue-50 border border-blue-200 text-blue-900 px-4 py-3 rounded">
              {result.summary}
            </div>
          )}

          {result.assumption && (
            <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded text-sm">
              <span className="font-medium">Assumption:</span> {result.assumption}
            </div>
          )}

          {result.chart && result.chart !== "table" && (
            <ResultChart
              chart={result.chart}
              columns={result.columns}
              rows={result.rows}
            />
          )}

          {result.columns.length > 0 && (
            <div className="bg-white border border-gray-200 rounded p-4">
              <ResultTable
                columns={result.columns}
                rows={result.rows}
                truncated={result.truncated}
              />
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded">
            <button
              onClick={() => setSqlOpen(!sqlOpen)}
              className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50"
            >
              <span className="text-sm font-medium text-gray-700">
                SQL executed{" "}
                {result.attempts > 1
                  ? `(fixed after ${result.attempts - 1} retr${
                      result.attempts - 1 === 1 ? "y" : "ies"
                    })`
                  : ""}
              </span>
              <span className="text-xs text-gray-500">{sqlOpen ? "▾" : "▸"}</span>
            </button>
            {sqlOpen && result.sql && (
              <pre className="px-4 pb-4 text-xs font-mono whitespace-pre-wrap text-gray-800 overflow-x-auto">
                {result.sql}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}