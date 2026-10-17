import { createContext } from "react";

export interface StoredConn {
  id: number;
  name: string;
  dialect: string;
}

export interface ConnectionCtx {
  active: StoredConn | null;
  setActive: (c: StoredConn | null) => void;
}

export const ConnectionContext = createContext<ConnectionCtx>({
  active: null,
  setActive: () => {},
});