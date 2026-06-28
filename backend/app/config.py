"""应用配置 - 通过环境变量加载，pydantic-settings 自动验证类型。

不写死任何 URL / API key。所有敏感配置走 .env 环境变量。
"""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Workflow Discovery Agent"
    version: str = "0.1.0"
    debug: bool = False

    # CORS（前端开发服务器地址）
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database (Postgres + asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/wda"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # LLM Provider: anthropic (default) or openai
    llm_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("llm_provider", "provider"),
    )

    # Anthropic / Claude protocol (also used by 火山引擎方舟 Claude 兼容协议)
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("llm_api_key", "volc_api_key"),
    )
    llm_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/coding",
        validation_alias=AliasChoices("llm_base_url", "volc_base_url"),
    )
    llm_model: str = Field(
        default="ark-code-latest",
        validation_alias=AliasChoices("llm_model", "volc_model"),
    )

    # OpenAI-compatible providers (Agnes, etc.)
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("openai_api_key", "agnes_api_key"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("openai_base_url", "agnes_base_url"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("openai_model", "agnes_model"),
    )

    # Legacy explicit Anthropic settings (kept for compatibility)
    anthropic_api_key: str = ""
    anthropic_model_haiku: str = "claude-haiku-4-5"
    anthropic_model_sonnet: str = "claude-sonnet-4-6"
    anthropic_model_opus: str = "claude-opus-4-7"

    # Search
    serpapi_key: str = ""
    serpapi_default_num: int = 15

    # Agent
    agent_max_iterations: int = 20
    agent_max_tokens_per_call: int = 4096
    agent_score_threshold: float = 7.0

    # 生成项目存储路径
    generated_projects_dir: str = "generated-projects"

    # JWT
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7


settings = Settings()
