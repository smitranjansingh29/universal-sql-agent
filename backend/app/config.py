from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    app_database_url: str = "sqlite:///./app.db"
    fernet_key: str
    groq_api_key: str = ""
    max_rows: int = 500
    query_timeout_seconds: int = 10
    max_retries: int = 2
    allow_custom_connections: bool = True
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
