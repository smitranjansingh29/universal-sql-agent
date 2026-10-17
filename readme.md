# Universal Text-to-SQL Analytics Agent
### Project Documentation & Architecture Guide

live link : https://universal-sql-agent.vercel.app/connect

**Author:** Smit Ranjan Singh
**Status:** Deployed (Live) 
**Stack:** React, FastAPI, Neon (PostgreSQL + pgvector), Groq, FastEmbed

---

## 1. Executive Summary

The Universal Text-to-SQL Analytics Agent is a database-agnostic AI application that allows users to connect to any SQL database, ask questions in plain English, and receive back a data table, a visual chart, and the exact SQL query that was executed. 

Unlike standard text-to-SQL demos that hardcode table names and dialects, this system dynamically introspects the schema, automatically drafts semantic descriptions for tables and columns using an LLM, and uses Retrieval-Augmented Generation (RAG) to handle large schemas efficiently.

---

## 2. Core Features

- **Database Agnostic:** Connects to Postgres, MySQL, and SQLite via SQLAlchemy.
- **Self-Learning Schema Layer:** Automatically generates descriptions for tables and columns so the LLM understands the business context of cryptic database names.
- **RAG (Retrieval-Augmented Generation):** For databases with more than 15 tables, the agent embeds the schema into a vector database and retrieves only the relevant tables needed to answer a question.
- **Five-Layer Security:** Prevents destructive queries via read-only accounts, AST validation (`sqlglot`), row limits, query timeouts, and read-only transactions.
- **Smart Error Recovery:** If a query fails (e.g., a hallucinated column), the agent reads the exact database error and retries with corrected SQL (up to 2 retries).
- **Dynamic Charting:** The LLM suggests a chart type (bar, line, pie, table) based on the data returned, which is rendered client-side using Recharts.

---

## 3. Architecture Diagram

The system runs on a two-phase pipeline:

### Setup Phase (Runs once per database)
1. **Connect:** User inputs a SQLAlchemy connection URL.
2. **Introspect:** The backend uses SQLAlchemy Inspector to read tables, columns, primary keys, and foreign keys.
3. **Draft:** `gpt-oss-120b` (via Groq) writes natural language descriptions for each table.
4. **Embed:** `fastembed` (BAAI/bge-small-en-v1.5) converts those descriptions into 384-dimensional vectors.
5. **Store:** Vectors are saved in Neon Postgres using the `pgvector` extension.

### Query Phase (Runs for every question)
1. **Retrieve:** The user's question is embedded. The system fetches the top 8 most similar schema chunks.
2. **Expand:** The system looks at the foreign keys of the retrieved tables and automatically pulls in any related tables (join neighbors).
3. **Generate:** The LLM receives the question + the filtered schema and outputs a strict JSON payload containing the SQL, chart type, and assumptions.
4. **Validate:** `sqlglot` parses the SQL into an Abstract Syntax Tree (AST) to enforce `SELECT`-only, validate table names against an allow-list, and append a `LIMIT 500`.
5. **Execute:** The query runs against the target database inside a read-only transaction with a 10-second timeout.
6. **Summarize:** The first 20 rows of the result are sent to a cheap LLM to write a one-sentence summary.

---

## 4. Technology Stack

### Backend
* **Framework:** FastAPI + Pydantic v2
* **Database (App State):** Neon PostgreSQL (with `pgvector`)
* **Target DB Connectors:** SQLAlchemy 2.0 (`psycopg`, `pymysql`, `sqlite3`)
* **SQL Validation:** `sqlglot`
* **LLM (SQL Generation):** Groq (`openai/gpt-oss-120b`)
* **Embeddings:** `fastembed` (`BAAI/bge-small-en-v1.5` - local, zero API cost)
* **Security:** `cryptography.Fernet` (encrypts database URLs at rest)

### Frontend
* **Framework:** React + Vite + TypeScript
* **Styling:** Tailwind CSS
* **State Management:** TanStack Query + React Context
* **Charts:** Recharts
* **Routing:** React Router DOM

### Infrastructure
* **Backend Host:** Render (Dockerized)
* **Frontend Host:** Vercel
* **Database Host:** Neon

---

## 5. Security Model (Five Layers)

Because LLMs can be tricked into generating malicious SQL, the system does not rely on prompt engineering for security. It uses five independent layers:

1. **Read-Only Account:** The system strongly advises using a database user with read-only permissions.
2. **AST Validation (`sqlglot`):** The validator parses the SQL and rejects:
   - Multiple statements (e.g., `SELECT ...; DROP TABLE ...`)
   - Any write operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`)
   - Disallowed tables (not in the connected schema)
   - Dangerous functions (e.g., `pg_sleep`, `load_extension`)
   - Sensitive columns (e.g., `password`, `api_key`)
3. **Row Limits:** A `LIMIT 500` is enforced if the LLM forgets one.
4. **Query Timeouts:** Postgres uses `SET LOCAL statement_timeout`; MySQL uses `MAX_EXECUTION_TIME`.
5. **Read-Only Transactions:** Executed via `SET TRANSACTION READ ONLY` or `PRAGMA query_only = ON`.

---

## 6. Evaluation & Accuracy

We tested the agent on the Northwind database (14 tables, ~830 orders). 

**Test Configuration:**
- 10 hand-verified questions (3 easy, 4 medium, 3 hard).
- RAG threshold set to `5` (forcing the system to use RAG instead of the full schema).
- Execution accuracy measured by comparing the *values* of the predicted SQL result against a gold-standard SQL result.

**Results:**
| Tier | Correct | Total | Accuracy |
| :--- | :--- | :--- | :--- |
| Easy | 3 | 3 | 100% |
| Medium | 4 | 4 | 100% |
| Hard | 3 | 3 | 100% |
| **Overall** | **10** | **10** | **100%** |

*Note: On a 10-question set, this indicates the pipeline is working correctly. Refusal accuracy (unanswerable questions) was 100%, and attack block rate (adversarial prompts) was 100%.*

---

## 7. Key Engineering Decisions

**1. Why `sqlglot` instead of Regex?**
Regex is notoriously bad at parsing SQL. `sqlglot` converts SQL into an AST, allowing us to safely check exactly which tables are being queried, regardless of dialect (SQLite vs Postgres).

**2. Why local embeddings (`fastembed`) instead of OpenAI?**
Initially, we used OpenAI's `text-embedding-3-small`. However, API costs, rate limits, and deployment memory limits (Render's free tier has 512MB) made it impractical. `fastembed` uses ONNX runtime instead of PyTorch, keeping memory usage under 100MB and costing $0.

**3. Why RAG with Foreign Key Expansion?**
Standard RAG might retrieve the `Orders` table but miss the `Customers` table. By reading the foreign keys from SQLAlchemy, we automatically pull in tables that are connected to the retrieved tables, ensuring joins always have their required context.

**4. The Schema Editor**
The biggest accuracy lever in text-to-SQL is human-readable descriptions. A table named `t_ord_hdr` will fail until a human explains it. The UI includes a feature to edit these descriptions, which sets a `user_edited` flag in the database so the auto-indexer never overwrites human corrections.

---

## 8. Deployment Guide

### Environment Variables (Backend)
- `APP_DATABASE_URL`: `postgresql+psycopg://...` (Neon connection string)
- `GROQ_API_KEY`: Groq API key
- `FERNET_KEY`: Fernet encryption key for connection URLs
- `CORS_ORIGINS`: Frontend URL (e.g., `https://my-app.vercel.app`)

### Local Development
1. `cd backend`
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Production Deployment
1. **Neon:** Create a Postgres project, enable `CREATE EXTENSION vector;`, and run the app tables SQL.
2. **Render:** Create a Web Service, connect GitHub, set Root Directory to `backend`, select Docker as the environment. Render will use the `Dockerfile` to build the image.
3. **Vercel:** Import GitHub repo, set Root Directory to `frontend`, configure Vite, and set the `VITE_API_URL` environment variable to the Render backend URL.

---

## 9. What I Learned / Future Improvements

- **LLM Non-Determinism:** Even with `temperature=0`, LLMs occasionally return malformed JSON. We solved this by implementing Pydantic validation on the LLM's response and a retry loop.
- **Windows vs. Linux Line Endings:** Pushing a repo with CRLF line endings caused bash errors when rendering the Dockerfile. This was solved by adding a `.gitattributes` file.
- **Stretch Goals:** 
  - Add support for Snowflake/BigQuery.
  - Implement Server-Sent Events (SSE) to stream the SQL generation stages to the frontend.
  - Add conversation memory ("Now filter that by Germany").