import type { Connection, QueryResponse } from "./types";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text.slice(0, 300)}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${API}/api/health`).then((r) => json<{ ok: boolean }>(r)),

  listConnections: () =>
    fetch(`${API}/api/connections`).then((r) => json<Array<{ id: number; name: string; dialect: string }>>(r)),

  createConnection: (name: string, url: string) =>
    fetch(`${API}/api/connections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, url }),
    }).then((r) => json<Connection>(r)),

  ask: (connectionId: number, question: string) =>
    fetch(`${API}/api/connections/${connectionId}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }).then((r) => json<QueryResponse>(r)),
};