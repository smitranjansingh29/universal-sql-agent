"""
Validator unit tests. Runs offline — no LLM, no app server.

Run:
    cd backend
    pytest tests/test_validator.py -v
"""

import pytest
from app.validator import validate, ValidationError

ALLOWED = {"users", "orders"}

# Each case: (input, dialect, expected_raises)
ATTACKS = [
    # (attack_sql, dialect, should_raise)
    ("DROP TABLE users", "sqlite", True),
    ("DELETE FROM users", "sqlite", True),
    ("INSERT INTO users (name) VALUES ('x')", "sqlite", True),
    ("UPDATE orders SET total = 0", "sqlite", True),
    ("CREATE TABLE evil (id int)", "sqlite", True),
    ("ALTER TABLE users ADD COLUMN role TEXT", "sqlite", True),
    ("SELECT * FROM users; DROP TABLE users", "sqlite", True),
    ("SELECT * FROM sqlite_master", "sqlite", True),
    ("SELECT * FROM users WHERE id = 1; -- comment\nDELETE FROM users", "sqlite", True),
    ("SELECT load_extension('x')", "sqlite", True),
    ("SELECT * FROM secret_table", "sqlite", True),
    ("SELECT password FROM users", "sqlite", True),
    ("SELECT api_key FROM users", "sqlite", True),
    # MySQL / Postgres specific
    ("SELECT * FROM users; DROP TABLE users", "postgres", True),
    ("SELECT sleep(10)", "postgres", True),
    ("SELECT pg_sleep(10)", "postgres", True),
    ("SELECT * FROM users LIMIT 10; DELETE FROM orders", "mysql", True),
    # Should pass
    ("SELECT * FROM users", "sqlite", False),
    ("SELECT COUNT(*) FROM orders", "sqlite", False),
    (
        "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id",
        "sqlite",
        False,
    ),
    (
        "SELECT * FROM users WHERE id = 1 OR 1=1",
        "sqlite",
        False,
    ),  # documented limitation
    ("WITH x AS (SELECT * FROM users) SELECT * FROM x", "sqlite", False),
]


@pytest.mark.parametrize("sql,dialect,should_raise", ATTACKS)
def test_attack_suite(sql, dialect, should_raise):
    if should_raise:
        with pytest.raises(ValidationError):
            validate(sql, dialect, ALLOWED, max_rows=500)
    else:
        result = validate(sql, dialect, ALLOWED, max_rows=500)
        assert isinstance(result, str) and result, "expected valid SQL"


def test_limit_injected():
    out = validate("SELECT * FROM users", "sqlite", ALLOWED, max_rows=100)
    assert "LIMIT 100" in out.upper()


def test_existing_limit_preserved():
    out = validate("SELECT * FROM users LIMIT 5", "sqlite", ALLOWED, max_rows=500)
    assert "LIMIT 5" in out.upper()
    assert "LIMIT 500" not in out.upper()


def test_multi_statement_blocked():
    with pytest.raises(ValidationError):
        validate("SELECT * FROM users; SELECT * FROM orders", "sqlite", ALLOWED)


def test_non_select_blocked():
    with pytest.raises(ValidationError):
        validate("VACUUM", "sqlite", ALLOWED)


def test_cte_with_write_blocked():
    with pytest.raises(ValidationError):
        validate(
            "WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x",
            "postgres",
            ALLOWED,
        )


def test_sensitive_column_blocked():
    with pytest.raises(ValidationError):
        validate("SELECT password FROM users", "postgres", ALLOWED)


def test_case_insensitive_table_check():
    with pytest.raises(ValidationError):
        validate("SELECT * FROM USERS", "sqlite", {"orders"})


def test_allowed_table_passes():
    out = validate("SELECT id FROM orders", "sqlite", ALLOWED)
    assert "orders" in out.lower()
