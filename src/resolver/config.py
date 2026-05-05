from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | str = ""
    github_token: str = ""
    langsmith_api_key: str | None = None
    default_model: str = "gpt-4o-mini"
    coder_model: str = "gpt-4.1-mini"
    embed_model: str = "text-embedding-3-small"
    chroma_dir: str = "./.chroma"
    work_dir: str = "./.work"

    @property
    def has_openai_key(self) -> bool:
        key = self.openai_api_key.get_secret_value() if isinstance(self.openai_api_key, SecretStr) else self.openai_api_key.strip()
        return bool(key) and "..." not in key

    @property
    def has_github_token(self) -> bool:
        key = self.github_token.strip()
        return bool(key) and "..." not in key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
