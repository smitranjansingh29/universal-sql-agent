from sqlalchemy import text
from app.chunking import embed_question  # Import the new function

SMALL_SCHEMA_THRESHOLD = 5  # Set to 5 to test RAG on Northwind


async def retrieve(
    question: str, connection_id: int, all_tables: list[dict], db_session
) -> dict:
    # Small databases send full schema directly, large databases use RAG retrieval
    if len(all_tables) <= SMALL_SCHEMA_THRESHOLD:
        return {"mode": "full_schema", "tables": all_tables}

    # 1. Embed the question (using 768 dims now)
    q_emb = await embed_question(question)

    # 2. Retrieve the 8 most similar chunks from Neon
    rows = db_session.execute(
        text("""
            SELECT table_name FROM schema_chunks
            WHERE connection_id = :cid AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT 8
        """),
        {"cid": connection_id, "emb": str(q_emb)},
    ).fetchall()

    # 3. Expand based on foreign keys
    hit_tables = {r[0] for r in rows if r[0]}
    expanded = set(hit_tables)
    for t in all_tables:
        if t["name"] in hit_tables:
            for fk in t["fks"]:
                expanded.add(fk["ref_table"])
        for fk in t["fks"]:
            if fk["ref_table"] in hit_tables:
                expanded.add(t["name"])

    final_tables = [t for t in all_tables if t["name"] in expanded]
    return {"mode": "rag", "tables": final_tables}


# from sqlalchemy import text
# from openai import AsyncOpenAI
# from app.config import settings

# openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
# SMALL_SCHEMA_THRESHOLD = 15  # Databases with less than or equal to 15 tables skip RAG and use full schema directly


# async def retrieve(
#     question: str, connection_id: int, all_tables: list[dict], db_session
# ) -> dict:
#     # Small databases send full schema directly, large databases use RAG retrieval
#     if len(all_tables) <= SMALL_SCHEMA_THRESHOLD:
#         return {"mode": "full_schema", "tables": all_tables}

#     # 1. Embed the question
#     resp = await openai_client.embeddings.create(
#         model="text-embedding-3-small", input=question
#     )
#     q_emb = resp.data[0].embedding

#     # 2. Retrieve the 8 most similar chunks from Neon
#     rows = db_session.execute(
#         text("""
#             SELECT table_name FROM schema_chunks
#             WHERE connection_id = :cid AND embedding IS NOT NULL
#             ORDER BY embedding <=> CAST(:emb AS vector)
#             LIMIT 8
#         """),
#         {"cid": connection_id, "emb": str(q_emb)},
#     ).fetchall()

#     # 3. Expand based on foreign keys (if a table is retrieved, also include tables it relates to)
#     hit_tables = {r[0] for r in rows if r[0]}
#     expanded = set(hit_tables)
#     for t in all_tables:
#         if t["name"] in hit_tables:
#             for fk in t["fks"]:
#                 expanded.add(fk["ref_table"])
#         for fk in t["fks"]:
#             if fk["ref_table"] in hit_tables:
#                 expanded.add(t["name"])

#     final_tables = [t for t in all_tables if t["name"] in expanded]
#     return {"mode": "rag", "tables": final_tables}
