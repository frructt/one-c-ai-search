from __future__ import annotations

import logging

from api.query_expansion import expand_query
from api.rerank import build_why, rerank
from api.schemas import CandidateResponse, FindChangePlacesResponse
from api.weaviate_search import WeaviateSearch, WeaviateSearchError
from common.settings import Settings
from indexer.embedder_client import EmbeddingClient, EmbeddingError


LOGGER = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingClient | None = None,
        search_backend: WeaviateSearch | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or EmbeddingClient(
            base_url=settings.embeddings_base_url,
            model=settings.embeddings_model,
            timeout_seconds=settings.embedding_timeout_seconds,
            retries=settings.embedding_retries,
            text_limit=settings.embedding_text_limit,
        )
        self.search_backend = search_backend or WeaviateSearch(settings)

    def close(self) -> None:
        self.embedder.close()
        self.search_backend.close()

    def find_change_places(
        self,
        *,
        query: str,
        repo: str,
        branch: str,
        limit: int,
    ) -> FindChangePlacesResponse:
        self.settings.validate_repo_branch(repo, branch)
        limit = self.settings.clamp_limit(limit)
        expanded_query = expand_query(query)
        internal_limit = self.settings.internal_search_limit(limit)
        LOGGER.info("search query repo=%s branch=%s limit=%s", repo, branch, limit)

        query_vector = self.embedder.embed(expanded_query)
        items = self.search_backend.search(
            query=expanded_query,
            query_vector=query_vector,
            repo=repo,
            branch=branch,
            limit=internal_limit,
        )
        LOGGER.info("number of results: %s", len(items))
        ranked = rerank(items, expanded_query)[:limit]
        candidates = [
            build_candidate_response(rank=index + 1, item=item, query=expanded_query)
            for index, item in enumerate(ranked)
        ]
        return FindChangePlacesResponse(
            query=query,
            expanded_query=expanded_query,
            repo=repo,
            branch=branch,
            candidates=candidates,
        )


def build_candidate_response(*, rank: int, item: dict, query: str) -> CandidateResponse:
    score = float(item.get("score") or 0.0)
    final_score = float(item.get("final_score", score))
    return CandidateResponse(
        rank=rank,
        path=str(item.get("path") or ""),
        gitlab_url=str(item.get("gitlab_url") or ""),
        module_name=str(item.get("module_name") or ""),
        object_type=str(item.get("object_type") or ""),
        symbol_name=str(item.get("symbol_name") or ""),
        symbol_type=str(item.get("symbol_type") or ""),
        start_line=int(item.get("start_line") or 0),
        end_line=int(item.get("end_line") or 0),
        score=score,
        final_score=final_score,
        why=build_why(item, query),
        code_preview=make_code_preview(str(item.get("code") or "")),
    )


def make_code_preview(code: str, limit: int = 1500) -> str:
    normalized = code.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n... [truncated]"


__all__ = [
    "EmbeddingError",
    "SearchService",
    "WeaviateSearchError",
    "build_candidate_response",
    "make_code_preview",
]
