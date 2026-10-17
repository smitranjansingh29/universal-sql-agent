import json
from openai import AsyncOpenAI
from sqlalchemy import text
from app.config import settings
from sentence_transformers import SentenceTransformer

groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,
)

# Local embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


def _to_pg_vector(embedding: list[float]) -> str:
    """Convert a python list of floats to a pgvector string format."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def embed_batch(texts: list[str]) -> list[str]:
    """Embed multiple strings locally and return pgvector formatted strings."""
    embeddings = embed_model.encode(texts, convert_to_numpy=True)
    return [_to_pg_vector(e.tolist()) for e in embeddings]


async def embed_question(question: str) -> str:
    """Embed a single question locally and return pgvector formatted string."""
    emb = embed_model.encode(question, convert_to_numpy=True).tolist()
    return _to_pg_vector(emb)


async def draft_table_description(table: dict) -> dict:
    """Use Groq's Llama model to draft descriptions."""
    col_lines = [f"  - {c['name']} ({c['type']})" for c in table["columns"]]
    fk_lines = [
        f"  FK: {fk['cols']} -> {fk['ref_table']}.{fk['ref_cols']}"
        for fk in table["fks"]
    ]

    prompt = f"""Document this database table for a text-to-SQL agent.
Table: {table['name']}
Columns:
{chr(10).join(col_lines)}
{chr(10).join(fk_lines)}
Return ONLY valid JSON in this format: {{"description": "...", "columns": {{"col_name": "desc"}}}}"""

    try:
        resp = await groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"Failed to draft description for {table['name']}: {e}")
        return {"description": "", "columns": {}}


def build_table_chunk(table: dict, draft: dict) -> str:
    """Combine table name, description, columns, foreign keys into one text chunk."""
    lines = [f"TABLE: {table['name']}"]
    if draft.get("description"):
        lines.append(f"DESCRIPTION: {draft['description']}")
    lines.append("COLUMNS:")
    for c in table["columns"]:
        desc = draft.get("columns", {}).get(c["name"], "")
        suffix = f" — {desc}" if desc and desc != "unclear" else ""
        lines.append(f"  {c['name']} ({c['type']}){suffix}")
    for fk in table["fks"]:
        lines.append(f"  FK: {fk['cols']} -> {fk['ref_table']}.{fk['ref_cols']}")
    return "\n".join(lines)


# import json
# from openai import AsyncOpenAI
# from sqlalchemy import text
# from app.config import settings

# # Use OpenAI for embeddings (Groq does not provide embedding models)
# openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


# async def embed_batch(texts: list[str]) -> list[list[float]]:
#     resp = await openai_client.embeddings.create(
#         model="text-embedding-3-small",
#         input=texts,
#         dimensions=1536,
#     )
#     return [d.embedding for d in resp.data]


# async def draft_table_description(table: dict) -> dict:
#     # Call LLM to generate description for table and columns
#     col_lines = [f"  - {c['name']} ({c['type']})" for c in table["columns"]]
#     fk_lines = [
#         f"  FK: {fk['cols']} -> {fk['ref_table']}.{fk['ref_cols']}"
#         for fk in table["fks"]
#     ]

#     prompt = f"""Document this database table for a text-to-SQL agent.
# Table: {table['name']}
# Columns:\n{chr(10).join(col_lines)}
# {chr(10).join(fk_lines)}
# Return JSON: {{"description": "...", "columns": {{"col_name": "desc"}}}}"""

#     resp = await openai_client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         response_format={"type": "json_object"},
#         temperature=0,
#     )
#     return json.loads(resp.choices[0].message.content)


# def build_table_chunk(table: dict, draft: dict) -> str:
#     # Combine table name, description, columns, foreign keys into one text chunk
#     lines = [f"TABLE: {table['name']}"]
#     if draft.get("description"):
#         lines.append(f"DESCRIPTION: {draft['description']}")
#     lines.append("COLUMNS:")
#     for c in table["columns"]:
#         desc = draft.get("columns", {}).get(c["name"], "")
#         suffix = f" — {desc}" if desc and desc != "unclear" else ""
#         lines.append(f"  {c['name']} ({c['type']}){suffix}")
#     for fk in table["fks"]:
#         lines.append(f"  FK: {fk['cols']} -> {fk['ref_table']}.{fk['ref_cols']}")
#     return "\n".join(lines)
