import { useEffect, useState, type ReactNode } from "react";
import { ConnectionContext, type StoredConn } from "./ConnectionContextDef";

const KEY = "usql.activeConnection";

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<StoredConn | null>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? (JSON.parse(raw) as StoredConn) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (active) localStorage.setItem(KEY, JSON.stringify(active));
      else localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, [active]);

  return (
    <ConnectionContext.Provider value={{ active, setActive }}>
      {children}
    </ConnectionContext.Provider>
  );
}