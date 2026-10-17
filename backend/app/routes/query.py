from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import get_db
from app.crypto import decrypt_url
from app.models import Connection
from app.agent import answer

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql: str | None = None
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    truncated: bool = False
    summary: str | None = None
    assumption: str | None = None
    chart: str | None = None
    attempts: int = 0
    error: str | None = None
    detail: str | None = None
    retrieval_mode: str | None = None


@router.post("/connections/{conn_id}/query", response_model=QueryResponse)
async def run_query(conn_id: int, payload: QueryRequest, db: Session = Depends(get_db)):
    conn_row = db.query(Connection).filter(Connection.id == conn_id).first()
    if not conn_row:
        raise HTTPException(status_code=404, detail="Connection not found")

    url = decrypt_url(conn_row.url_encrypted)
    engine = create_engine(url, pool_pre_ping=True)

    try:
        # FIXED: Passing connection_id and db session to the agent
        result = await answer(payload.question, engine, conn_row.dialect, conn_id, db)
    finally:
        engine.dispose()

    if "error" in result:
        return QueryResponse(
            error=result["error"], detail=result.get("detail") or result.get("reason")
        )

    return QueryResponse(**result)
