from typing import Literal
from pydantic import BaseModel, Field, AliasChoices
from openai import AsyncOpenAI
from app.config import settings


class SqlPlan(BaseModel):
    can_answer: bool = True
    sql: str | None = Field(default=None, validation_alias=AliasChoices("sql", "query"))
    assumption: str | None = None
    chart: Literal["bar", "line", "pie", "table"] | None = None
    x: str | None = None
    y: list[str] | None = None
    reason: str | None = None

    def model_post_init(self, __context):
        # Normalize None to defaults after validation
        if self.chart is None:
            self.chart = "table"
        if self.y is None:
            self.y = []


client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,
)

MODEL = "openai/gpt-oss-120b"


async def call_llm(messages: list[dict]) -> SqlPlan:
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        # response_format removed — Groq gpt-oss-120b is unreliable with it
        temperature=0,
    )
    content = resp.choices[0].message.content
    try:
        return SqlPlan.model_validate_json(content)
    except Exception as e:
        raise ValueError(
            f"LLM did not return valid SqlPlan JSON. Raw: {content[:300]!r}. Error: {e}"
        )


async def summarize(question: str, rows: list[list]) -> str:
    preview = rows[:20]
    prompt = (
        f"Question: {question}\n"
        f"Here are the first {len(preview)} rows of the result: {preview}\n"
        f"Write one short sentence describing what the data shows. "
        f"Do not invent numbers not present in the rows."
    )
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()
