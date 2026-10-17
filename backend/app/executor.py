from sqlalchemy import text
from app.config import settings


def execute(engine, sql: str, dialect: str):
    with engine.connect() as conn:
        if dialect == "postgresql":
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(
                text(
                    f"SET LOCAL statement_timeout = '{settings.query_timeout_seconds}s'"
                )
            )
        elif dialect == "mysql":
            conn.execute(text("START TRANSACTION READ ONLY"))
            conn.execute(
                text(
                    f"SET SESSION MAX_EXECUTION_TIME = {settings.query_timeout_seconds * 1000}"
                )
            )
        elif dialect == "sqlite":
            conn.execute(text("PRAGMA query_only = ON"))

        result = conn.execute(text(sql))
        rows = result.fetchmany(settings.max_rows + 1)
        truncated = len(rows) > settings.max_rows
        rows = rows[: settings.max_rows]
        columns = list(result.keys())
        conn.rollback()

    return {
        "columns": columns,
        "rows": [list(r) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }
