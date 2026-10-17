import logging
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

BLOCKED_FUNCS = {
    "pg_sleep",
    "pg_read_file",
    "pg_ls_dir",
    "lo_import",
    "lo_export",
    "load_file",
    "sleep",
    "benchmark",
    "readfile",
    "load_extension",
}

# Hardcoded for now — Phase 4 will move this to per-connection config
SENSITIVE_COLUMNS = {"password", "password_hash", "pwd", "secret", "token", "api_key"}


class ValidationError(Exception):
    pass


def validate(
    sql: str, dialect: str, allowed_tables: set[str], max_rows: int = 500
) -> str:
    dialect_map = {"postgresql": "postgres", "mysql": "mysql", "sqlite": "sqlite"}
    sg_dialect = dialect_map.get(dialect, dialect)

    logger.info("VALIDATE input (%s): %r", sg_dialect, sql)

    try:
        statements = sqlglot.parse(sql, read=sg_dialect)
    except sqlglot.errors.ParseError as e:
        raise ValidationError(f"Could not parse SQL: {e}")

    statements = [s for s in statements if s is not None]
    logger.info("VALIDATE parsed %d statement(s)", len(statements))

    if len(statements) != 1:
        raise ValidationError(
            f"Exactly one statement is allowed, got {len(statements)}"
        )

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        raise ValidationError(
            f"Only SELECT queries are allowed, got {type(tree).__name__}"
        )

    banned = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Into,
    )
    if tree.find(*banned):
        raise ValidationError("Write or DDL operations are not allowed")

    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}

    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name not in allowed_tables and name not in cte_names:
            raise ValidationError(f"Table not allowed: {table.name}")

    # NEW: block sensitive columns even when they are in an allowed table
    for col in tree.find_all(exp.Column):
        if col.name.lower() in SENSITIVE_COLUMNS:
            raise ValidationError(f"Column not allowed: {col.name}")

    for func in tree.find_all(exp.Func, exp.Anonymous):
        if func.name.lower() in BLOCKED_FUNCS:
            raise ValidationError(f"Function not allowed: {func.name}")

    if not tree.args.get("limit"):
        tree = tree.limit(max_rows)

    out = tree.sql(dialect=sg_dialect)
    logger.info("VALIDATE output: %r", out)
    return out
