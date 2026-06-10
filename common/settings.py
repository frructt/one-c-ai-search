from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _csv(value: str | None, fallback: list[str]) -> list[str]:
    if not value:
        return fallback
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or fallback


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float") from exc


def _path_from_env(name: str, default: str) -> Path:
    raw = os.getenv(name, default)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    repo_name: str
    repo_path: Path
    branch: str
    allowed_repos: list[str]
    allowed_branches: list[str]
    gitlab_base_url: str
    gitlab_project_path: str
    weaviate_url: str
    weaviate_api_key: str | None
    weaviate_grpc_host: str | None
    weaviate_grpc_port: int
    weaviate_grpc_secure: bool
    weaviate_collection: str
    weaviate_vector_name: str
    weaviate_batch_size: int
    embeddings_base_url: str
    embeddings_api_key: str
    embeddings_model: str
    embedding_batch_size: int
    embedding_text_limit: int
    embedding_timeout_seconds: int
    embedding_retries: int
    llm_query_expansion_enabled: bool
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: int
    llm_retries: int
    llm_max_tokens: int
    search_alpha: float
    search_internal_limit: int
    search_internal_limit_max: int
    indexer_fail_on_failed_files: bool
    api_default_limit: int
    api_max_limit: int
    api_host: str
    api_port: int
    metadata_weaviate_collection: str = "OneCMetadataObject"
    metadata_weaviate_vector_name: str = "metadata_vector"
    metadata_search_alpha: float = 0.35
    metadata_search_limit: int = 20
    metadata_boost_max: float = 0.25

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(env_file or PROJECT_ROOT / ".env")
        repo_name = os.getenv("REPO_NAME", "gp")
        branch = os.getenv("BRANCH", "master")
        settings = cls(
            repo_name=repo_name,
            repo_path=_path_from_env("REPO_PATH", "../1С ГП/gp_bsl"),
            branch=branch,
            allowed_repos=_csv(os.getenv("ALLOWED_REPOS"), [repo_name]),
            allowed_branches=_csv(os.getenv("ALLOWED_BRANCHES"), [branch]),
            gitlab_base_url=os.getenv("GITLAB_BASE_URL", "https://gitlab.company.ru").rstrip("/"),
            gitlab_project_path=os.getenv("GITLAB_PROJECT_PATH", "group/project").strip("/"),
            weaviate_url=os.getenv("WEAVIATE_URL", "http://localhost:8080").rstrip("/"),
            weaviate_api_key=os.getenv("WEAVIATE_API_KEY") or None,
            weaviate_grpc_host=os.getenv("WEAVIATE_GRPC_HOST") or None,
            weaviate_grpc_port=_int("WEAVIATE_GRPC_PORT", 50051),
            weaviate_grpc_secure=_bool(os.getenv("WEAVIATE_GRPC_SECURE"), False),
            weaviate_collection=os.getenv("WEAVIATE_COLLECTION", "OneCCodeChunk"),
            weaviate_vector_name=os.getenv("WEAVIATE_VECTOR_NAME", "code_vector"),
            weaviate_batch_size=max(1, _int("WEAVIATE_BATCH_SIZE", 64)),
            embeddings_base_url=os.getenv("EMBEDDINGS_BASE_URL", "http://localhost:8001/v1").rstrip("/"),
            embeddings_api_key=os.getenv("EMBEDDINGS_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY",
            embeddings_model=os.getenv("EMBEDDINGS_MODEL", "qwen3-embedder-8b"),
            embedding_batch_size=max(1, _int("EMBEDDING_BATCH_SIZE", 16)),
            embedding_text_limit=max(1000, _int("EMBEDDING_TEXT_LIMIT", 16000)),
            embedding_timeout_seconds=max(1, _int("EMBEDDING_TIMEOUT_SECONDS", 30)),
            embedding_retries=max(1, _int("EMBEDDING_RETRIES", 3)),
            llm_query_expansion_enabled=_bool(os.getenv("LLM_QUERY_EXPANSION_ENABLED"), False),
            llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:8002/v1").rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY",
            llm_model=os.getenv("LLM_MODEL", "qwen2.5-coder-32b-instruct"),
            llm_timeout_seconds=max(1, _int("LLM_TIMEOUT_SECONDS", 10)),
            llm_retries=max(1, _int("LLM_RETRIES", 1)),
            llm_max_tokens=max(32, _int("LLM_MAX_TOKENS", 512)),
            search_alpha=min(1.0, max(0.0, _float("SEARCH_ALPHA", 0.35))),
            search_internal_limit=max(1, _int("SEARCH_INTERNAL_LIMIT", 50)),
            search_internal_limit_max=max(1, _int("SEARCH_INTERNAL_LIMIT_MAX", 200)),
            indexer_fail_on_failed_files=_bool(os.getenv("INDEXER_FAIL_ON_FAILED_FILES"), True),
            api_default_limit=max(1, _int("API_DEFAULT_LIMIT", 10)),
            api_max_limit=max(1, _int("API_MAX_LIMIT", 50)),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=_int("API_PORT", 8000),
            metadata_weaviate_collection=os.getenv("METADATA_WEAVIATE_COLLECTION", "OneCMetadataObject"),
            metadata_weaviate_vector_name=os.getenv("METADATA_WEAVIATE_VECTOR_NAME", "metadata_vector"),
            metadata_search_alpha=min(1.0, max(0.0, _float("METADATA_SEARCH_ALPHA", 0.35))),
            metadata_search_limit=max(1, _int("METADATA_SEARCH_LIMIT", 20)),
            metadata_boost_max=max(0.0, _float("METADATA_BOOST_MAX", 0.25)),
        )
        if settings.search_internal_limit > settings.search_internal_limit_max:
            raise ValueError("SEARCH_INTERNAL_LIMIT must be <= SEARCH_INTERNAL_LIMIT_MAX")
        if settings.api_default_limit > settings.api_max_limit:
            raise ValueError("API_DEFAULT_LIMIT must be <= API_MAX_LIMIT")
        return settings

    def require_repo_path(self) -> None:
        if not self.repo_path.exists():
            raise FileNotFoundError(f"REPO_PATH does not exist: {self.repo_path}")
        if not (self.repo_path / "src").exists():
            raise FileNotFoundError(f"REPO_PATH must contain a src directory: {self.repo_path}")

    def validate_repo_branch(self, repo: str, branch: str) -> None:
        if repo not in self.allowed_repos:
            raise ValueError(f"repo '{repo}' is not allowed")
        if branch not in self.allowed_branches:
            raise ValueError(f"branch '{branch}' is not allowed")

    def clamp_limit(self, requested: int | None) -> int:
        value = requested or self.api_default_limit
        if value < 1:
            raise ValueError("limit must be >= 1")
        if value > self.api_max_limit:
            raise ValueError(f"limit must be <= {self.api_max_limit}")
        return value

    def internal_search_limit(self, user_limit: int) -> int:
        return min(self.search_internal_limit_max, max(self.search_internal_limit, user_limit * 5))

    def parsed_weaviate_url(self):
        parsed = urlparse(self.weaviate_url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("WEAVIATE_URL must include scheme and host")
        return parsed


def load_settings(env_file: Path | None = None) -> Settings:
    return Settings.from_env(env_file)
