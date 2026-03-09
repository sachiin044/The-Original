import os
from dataclasses import dataclass
from functools import lru_cache

from cryptography.fernet import Fernet
from dotenv import load_dotenv


load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _validate_fernet_key(key: str) -> None:
    try:
        Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise ConfigError(
            "Invalid CREDENTIAL_ENCRYPTION_KEY format (must be a valid Fernet key)"
        ) from exc


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_service_key: str
    credential_encryption_key: str

    pinecone_api_key: str | None = None
    pinecone_index_name: str | None = None


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        openai_api_key=_required_env("OPENAI_API_KEY"),
        supabase_url=_required_env("SUPABASE_URL"),
        supabase_service_key=_required_env("SUPABASE_SERVICE_KEY"),
        credential_encryption_key=_required_env("CREDENTIAL_ENCRYPTION_KEY"),

        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
        pinecone_index_name=os.getenv("PINECONE_INDEX_NAME"),
    )

    _validate_fernet_key(settings.credential_encryption_key)

    return settings


def validate_settings() -> None:
    get_settings()

settings = get_settings()

