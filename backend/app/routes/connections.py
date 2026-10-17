from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.crypto import encrypt_url, decrypt_url
from app.introspect import introspect_schema
from app.models import Connection
from app.config import settings

router = APIRouter(tags=["connections"])


class ConnectionCreate(BaseModel):
    name: str
    url: str


class ConnectionOut(BaseModel):
    id: int
    name: str
    dialect: str
    tables: list[dict] | None = None
    warning: str | None = None


@router.post("/connections", response_model=ConnectionOut)
def create_connection(payload: ConnectionCreate, db: Session = Depends(get_db)):
    """
    Accept a database URL, test it, encrypt it, save it, and return the schema.
    """
    if not settings.allow_custom_connections:
        raise HTTPException(status_code=403, detail="Custom connections are disabled")

    url = payload.url.strip()

    # Extract dialect from the URL prefix (postgresql+psycopg://, mysql+pymysql://, sqlite://)
    dialect = url.split("://")[0].split("+")[0]
    if dialect not in ("postgresql", "mysql", "sqlite"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported dialect: {dialect}. Use postgresql, mysql, or sqlite.",
        )

    # Test the connection before saving
    try:
        test_engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args=(
                {"connect_timeout": 5} if dialect in ("postgresql", "mysql") else {}
            ),
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

    # Warn if the account can write (harmless test, rolled back)
    warning = None
    try:
        with test_engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text("CREATE TEMPORARY TABLE _test_write (id int)"))
            trans.rollback()
            warning = "This account can write. Use a read-only user for production."
    except Exception:
        pass  # Write failed — good, account is likely read-only

    # Save encrypted
    conn_row = Connection(
        name=payload.name,
        dialect=dialect,
        url_encrypted=encrypt_url(url),
    )
    db.add(conn_row)
    db.commit()
    db.refresh(conn_row)

    # Introspect schema (non-blocking in production; synchronous here for simplicity)
    try:
        tables = introspect_schema(test_engine)
    except Exception as e:
        tables = None
        warning = (warning or "") + f" Introspection failed: {str(e)}"

    return ConnectionOut(
        id=conn_row.id,
        name=conn_row.name,
        dialect=conn_row.dialect,
        tables=tables,
        warning=warning,
    )


@router.get("/connections")
def list_connections(db: Session = Depends(get_db)):
    """List saved connections. Never return URLs."""
    rows = db.query(Connection).all()
    return [{"id": r.id, "name": r.name, "dialect": r.dialect} for r in rows]
