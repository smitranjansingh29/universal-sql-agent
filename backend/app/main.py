from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import connections, query, schema  # 1. MUST IMPORT SCHEMA

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Universal SQL Agent", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connections.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(schema.router, prefix="/api")  # 2. MUST INCLUDE SCHEMA ROUTER


@app.get("/api/health")
def health():
    return {"ok": True}
