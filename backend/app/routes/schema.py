from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import Session
import logging

from app.database import get_db, SessionLocal
from app.crypto import decrypt_url
from app.models import Connection, SchemaChunk
from app.introspect import introspect_schema
from app.chunking import draft_table_description, build_table_chunk, embed_batch

logger = logging.getLogger(__name__)
router = APIRouter(tags=["schema"])


class SchemaOut(BaseModel):
    tables: list[dict]
    dialect: str
    date_column: str | None = None


# ---------------------------------------------------------
# 1. GET SCHEMA ROUTE
# ---------------------------------------------------------
@router.get("/connections/{conn_id}/schema", response_model=SchemaOut)
def get_schema(conn_id: int, db: Session = Depends(get_db)):
    row = db.query(Connection).filter(Connection.id == conn_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")

    url = decrypt_url(row.url_encrypted)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        tables = introspect_schema(engine)
    finally:
        engine.dispose()

    return SchemaOut(tables=tables, dialect=row.dialect, date_column=row.date_column)


# ---------------------------------------------------------
# 2. INDEXING ROUTE
# ---------------------------------------------------------
@router.post("/connections/{conn_id}/index")
async def index_connection(
    conn_id: int, background: BackgroundTasks, db: Session = Depends(get_db)
):
    background.add_task(_index_worker, conn_id)
    return {"status": "indexing_started"}


async def _index_worker(conn_id: int):
    db = SessionLocal()
    try:
        row = db.query(Connection).filter(Connection.id == conn_id).first()
        if not row:
            return

        engine = create_engine(decrypt_url(row.url_encrypted))
        tables = introspect_schema(engine)

        # Clear old chunks (preserve manually edited ones)
        db.query(SchemaChunk).filter(
            SchemaChunk.connection_id == conn_id, SchemaChunk.user_edited == False
        ).delete()
        db.commit()

        chunks_to_embed = []
        for t in tables:
            draft = await draft_table_description(t)
            content = build_table_chunk(t, draft)
            chunks_to_embed.append(
                {"kind": "table", "table": t["name"], "content": content}
            )

        # Batch generate embeddings (returns list of pgvector strings)
        embeddings = await embed_batch([c["content"] for c in chunks_to_embed])

        # Insert using raw SQL to force the CAST(:emb AS vector)
        for chunk, emb_str in zip(chunks_to_embed, embeddings):
            db.execute(
                sql_text("""
                    INSERT INTO schema_chunks 
                    (connection_id, kind, table_name, content, embedding, user_edited)
                    VALUES (:cid, :kind, :tname, :content, CAST(:emb AS vector), FALSE)
                """),
                {
                    "cid": conn_id,
                    "kind": chunk["kind"],
                    "tname": chunk["table"],
                    "content": chunk["content"],
                    "emb": emb_str,
                },
            )

        db.commit()
        logger.info(
            f"Successfully indexed {len(chunks_to_embed)} tables for connection {conn_id}"
        )
    except Exception as e:
        db.rollback()  # Rollback in case of error so the transaction doesn't stay open
        logger.error(f"Indexing failed for connection {conn_id}: {e}")
    finally:
        db.close()
