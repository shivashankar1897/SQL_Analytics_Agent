from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loads application settings from backend/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_chat_deployment: str

      # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-north-1"


  # RDS PostgreSQL (read-only user)
    RDS_HOST: str
    RDS_PORT: int = 5432
    RDS_DB: str = "supportagent"
    RDS_USER: str
    RDS_PASSWORD: str

        # ElastiCache for Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379  
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_ENABLED: bool = True
    CACHE_TTL_QUERY_SECONDS: int = 600       # 10 minutes
    CACHE_TTL_SCHEMA_SECONDS: int = 3600     # 1 hour


    
    # LangSmith (observability)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "sql-analytics-agent"


        # Rate limiting / circuit breaker
    RATE_LIMIT_PER_MINUTE: int = 30
    INVESTIGATIVE_CALL_LIMIT_PER_SESSION: int = 30
    INVESTIGATIVE_CALL_WINDOW_SECONDS: int = 300

    # Application settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
   

   

    from urllib.parse import quote_plus

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.RDS_PASSWORD)

        return (
            f"postgresql+psycopg2://{self.RDS_USER}:{password}"
            f"@{self.RDS_HOST}:{self.RDS_PORT}/{self.RDS_DB}"
            f"?sslmode=require"
        )   

    model_config = {"env_file": ".env", "case_sensitive": True}






from urllib.parse import quote_plus

@property
def DATABASE_URL(self) -> str:
    password = quote_plus(self.RDS_PASSWORD)

    return (
        f"postgresql+psycopg2://{self.RDS_USER}:{password}"
        f"@{self.RDS_HOST}:{self.RDS_PORT}/{self.RDS_DB}"
        f"?sslmode=require"
    )



@lru_cache
def get_settings() -> Settings:
    """Create settings once and reuse them across the app."""
    return Settings()


settings = Settings()