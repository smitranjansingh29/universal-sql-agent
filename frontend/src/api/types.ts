export interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
}

export interface ForeignKey {
  cols: string[];
  ref_table: string;
  ref_cols: string[];
}

export interface TableInfo {
  schema: string;
  name: string;
  columns: TableColumn[];
  pk: string[];
  fks: ForeignKey[];
}

export interface Connection {
  id: number;
  name: string;
  dialect: string;
  tables?: TableInfo[];
  warning?: string | null;
}

export interface QueryRequest {
  question: string;
}

export interface QueryResponse {
  sql: string | null;
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
  summary: string | null;
  assumption: string | null;
  chart: "bar" | "line" | "pie" | "table" | null;
  attempts: number;
  error: string | null;
  detail: string | null;
}