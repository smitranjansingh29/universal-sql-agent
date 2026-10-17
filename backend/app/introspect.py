from sqlalchemy import inspect


def introspect_schema(engine, schemas: list[str] | None = None) -> list[dict]:
    """
    Read all tables, columns, primary keys, and foreign keys from a database.
    Works identically for Postgres, MySQL, and SQLite via SQLAlchemy Inspector.
    """
    insp = inspect(engine)
    tables = []
    target_schemas = schemas or [insp.default_schema_name]

    for schema in target_schemas:
        for table_name in insp.get_table_names(schema=schema):
            columns = []
            for col in insp.get_columns(table_name, schema=schema):
                columns.append(
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                    }
                )

            pk = insp.get_pk_constraint(table_name, schema=schema)
            fks = []
            for fk in insp.get_foreign_keys(table_name, schema=schema):
                fks.append(
                    {
                        "cols": fk["constrained_columns"],
                        "ref_table": fk["referred_table"],
                        "ref_cols": fk["referred_columns"],
                    }
                )

            tables.append(
                {
                    "schema": schema,
                    "name": table_name,
                    "columns": columns,
                    "pk": pk.get("constrained_columns", []),
                    "fks": fks,
                }
            )

    return tables
