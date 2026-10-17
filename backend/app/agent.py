from app.retrieval import retrieve
from app.llm import call_llm, summarize
from app.validator import validate, ValidationError
from app.executor import execute
from app.config import settings
from app.introspect import introspect_schema


def build_schema_text(tables: list[dict]) -> str:
    lines = []
    for t in tables:
        cols = ", ".join(f"{c['name']} {c['type']}" for c in t["columns"])
        lines.append(f"TABLE {t['name']} ({cols})")
        for fk in t["fks"]:
            lines.append(f"  FK: {fk['cols']} -> {fk['ref_table']}.{fk['ref_cols']}")
    return "\n".join(lines)


def pick_chart(plan, result) -> str:
    if plan.chart not in ("bar", "line", "pie", "table"):
        return "table"
    if plan.chart == "line" and plan.x:
        return "line" if result["row_count"] > 0 else "table"
    if plan.chart == "pie" and result["row_count"] <= 6:
        return "pie"
    if plan.chart == "bar" and result["row_count"] <= 30:
        return "bar"
    return "table"


async def answer(question: str, engine, dialect: str, connection_id: int, db_session):
    # 1. Introspect all tables to know what's available
    tables = introspect_schema(engine)
    allowed = {t["name"].lower() for t in tables}

    # 2. Retrieve relevant tables (using RAG)
    ctx = await retrieve(question, connection_id, tables, db_session)
    schema_text = build_schema_text(ctx["tables"])

    # 3. Build the prompt with the retrieved schema
    system = f"""You write one read-only SQL query for a {dialect} database.

Rules:
- Use only the tables and columns in SCHEMA. Never invent names.
- Write {dialect} syntax.
- Return only SELECT statements. No comments, no multiple statements.
- If the question cannot be answered from SCHEMA, set can_answer to false and explain in reason.
- If ambiguous, pick the most common reading and state it in assumption.

Return ONLY a JSON object with these exact fields:
{{
  "can_answer": true or false,
  "sql": "the SELECT statement" or null,
  "assumption": "your assumption or null",
  "chart": "bar" or "line" or "pie" or "table",
  "x": "column for x axis or null",
  "y": ["list of numeric columns for y axis"],
  "reason": "why not answerable or null"
}}

SCHEMA:
{schema_text}
"""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    last_error = None
    for attempt in range(1, settings.max_retries + 2):
        try:
            plan = await call_llm(messages)
        except Exception as e:
            return {"error": "llm_error", "detail": str(e)}

        if not plan.can_answer:
            return {"error": "cannot_answer", "reason": plan.reason}

        try:
            safe_sql = validate(plan.sql, dialect, allowed, settings.max_rows)
            result = execute(engine, safe_sql, dialect)
            summary = await summarize(question, result["rows"])
            return {
                **result,
                "sql": safe_sql,
                "summary": summary,
                "chart": pick_chart(plan, result),
                "attempts": attempt,
                "assumption": plan.assumption,
                "retrieval_mode": ctx["mode"],
            }
        except (ValidationError, Exception) as e:
            last_error = str(e)
            messages.append(
                {
                    "role": "user",
                    "content": f"Previous SQL failed: {plan.sql}\nError: {last_error}\nFix the query. Change only what the error requires.",
                }
            )

    return {"error": "max_retries", "detail": last_error}
