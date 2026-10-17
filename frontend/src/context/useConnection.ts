import { useContext } from "react";
import { ConnectionContext } from "./ConnectionContextDef";

export const useConnection = () => useContext(ConnectionContext);