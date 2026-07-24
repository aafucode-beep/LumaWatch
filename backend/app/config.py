"""应用配置：从环境变量 / .env 读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 鉴权
    app_password: str = "change-me-please"
    secret_key: str = "replace-with-a-long-random-secret"
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"

    # 数据库
    database_url: str = "sqlite:///./data/app.db"

    # 大模型（OpenAI 兼容）
    llm_base_url: str = "https://api.minimaxi.com/v1"
    llm_api_key: str = ""
    llm_model: str = "MiniMax-Text-01"
    llm_max_input_chars: int = 48000
    llm_timeout: int = 120

    # 爬取
    crawl_max_pages: int = 12
    crawl_timeout: int = 30
    crawl_delay: float = 1.5
    crawl_respect_robots: bool = True
    crawl_use_playwright: bool = True
    crawl_user_agent: str = "LightingIntelBot/1.0 (+personal research)"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
