import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Connection  # noqa: F401 — registers model


@pytest.fixture
def sqlite_engine(tmp_path):
    """In-memory SQLite engine with users/orders test schema."""
    path = tmp_path / "test_eval.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, "
            "total REAL, created_at TEXT, FOREIGN KEY (user_id) REFERENCES users(id))"
        )
        conn.exec_driver_sql(
            "INSERT INTO users (id, name, email) VALUES "
            "(1, 'Alice', 'a@x.com'), (2, 'Bob', 'b@x.com'), (3, 'Carol', 'c@x.com')"
        )
        conn.exec_driver_sql(
            "INSERT INTO orders (id, user_id, total, created_at) VALUES "
            "(1, 1, 10.0, '2026-01-01'), (2, 1, 20.0, '2026-01-05'), "
            "(3, 2, 15.0, '2026-01-10'), (4, 2, 25.0, '2026-01-15'), "
            "(5, 3, 30.0, '2026-01-20')"
        )
    yield engine
    engine.dispose()


@pytest.fixture
def app_db_session(tmp_path):
    """Isolated app DB for tests that need to persist models."""
    path = tmp_path / "app.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()
