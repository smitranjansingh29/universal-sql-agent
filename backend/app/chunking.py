import json
from openai import AsyncOpenAI
from sqlalchemy import text
from app.config import settings
from fastembed import TextEmbedding

groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,
)

# Lazy-load the model ONLY when needed (not at import time)
_embed_model = None


def _get_model():
    global _embed_model
    if _embed_model is None:
        # BAAI/bge-small-en-v1.5 outputs 384 dimensions, ~30MB
        _embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embed_model


def _to_pg_vector(embedding) -> str:
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


async def embed_batch(texts: list[str]) -> list[str]:
    model = _get_model()
    embeddings = list(model.embed(texts))
    return [_to_pg_vector(e) for e in embeddings]


async def embed_question(question: str) -> str:
    model = _get_model()
    embeddings = list(model.embed([question]))
    return _to_pg_vector(embeddings[0])


async def draft_table_description(table: dict) -> dict:
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
