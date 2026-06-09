from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.llm_query_expansion import LlmClient, expand_query_for_search
from api.rerank import build_why, rank_files
from api.schemas import CandidateResponse, FindChangePlacesResponse
from api.search_models import SearchCandidate, dedupe_candidates, default_retrieval_profiles
from api.weaviate_search import WeaviateSearch, WeaviateSearchError
from common.settings import Settings
from indexer.embedder_client import EmbeddingClient, EmbeddingError


LOGGER = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingClient | None = None,
        llm_expander: LlmClient | None = None,
        search_backend: WeaviateSearch | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or EmbeddingClient(
            base_url=settings.embeddings_base_url,
            api_key=settings.embeddings_api_key,
            model=settings.embeddings_model,
            timeout_seconds=settings.embedding_timeout_seconds,
            retries=settings.embedding_retries,
            text_limit=settings.embedding_text_limit,
        )
        self.llm_expander = llm_expander
        if self.llm_expander is None and settings.llm_query_expansion_enabled:
            self.llm_expander = LlmClient(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
                retries=settings.llm_retries,
                max_tokens=settings.llm_max_tokens,
            )
        self.search_backend = search_backend or WeaviateSearch(settings)

    def close(self) -> None:
        self.embedder.close()
        if self.llm_expander is not None:
            self.llm_expander.close()
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
        expanded_query = expand_query_for_search(query, self.llm_expander)
        internal_limit = self.settings.internal_search_limit(limit)
        LOGGER.info("search query repo=%s branch=%s limit=%s", repo, branch, limit)

        query_vector = self.embedder.embed(expanded_query)
        items = self._search_candidates(
            query=expanded_query,
            query_vector=query_vector,
            repo=repo,
            branch=branch,
            internal_limit=internal_limit,
        )
        LOGGER.info("number of results: %s", len(items))
        ranked = rank_files(dedupe_candidates(items), expanded_query)[:limit]
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

    def _search_candidates(
        self,
        *,
        query: str,
        query_vector: list[float],
        repo: str,
        branch: str,
        internal_limit: int,
    ) -> list[SearchCandidate]:
        profiles = default_retrieval_profiles(self.settings.search_alpha)
        max_workers = min(4, len(profiles))
        items: list[SearchCandidate] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.search_backend.search,
                    query=query,
                    query_vector=query_vector,
                    repo=repo,
                    branch=branch,
                    limit=profile.limit_for(internal_limit),
                    profile=profile,
                ): profile
                for profile in profiles
            }
            for future in as_completed(futures):
                profile = futures[future]
                profile_items = future.result()
                LOGGER.info("retrieval profile=%s results=%s", profile.name, len(profile_items))
                items.extend(profile_items)
        return items


def build_candidate_response(*, rank: int, item: SearchCandidate | dict, query: str) -> CandidateResponse:
    score = float(_candidate_value(item, "score") or 0.0)
    final_score = float(_candidate_value(item, "final_score") or score)
    return CandidateResponse(
        rank=rank,
        path=str(_candidate_value(item, "path") or ""),
        gitlab_url=str(_candidate_value(item, "gitlab_url") or ""),
        module_name=str(_candidate_value(item, "module_name") or ""),
        object_type=str(_candidate_value(item, "object_type") or ""),
        symbol_name=str(_candidate_value(item, "symbol_name") or ""),
        symbol_type=str(_candidate_value(item, "symbol_type") or ""),
        start_line=int(_candidate_value(item, "start_line") or 0),
        end_line=int(_candidate_value(item, "end_line") or 0),
        score=score,
        final_score=final_score,
        why=build_why(item, query),
        code_preview=make_code_preview(str(_candidate_value(item, "code") or "")),
    )


def make_code_preview(code: str, limit: int = 1500) -> str:
    normalized = code.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n... [truncated]"


def _candidate_value(item: SearchCandidate | dict, field: str):
    if isinstance(item, SearchCandidate):
        return getattr(item, field)
    return item.get(field)


__all__ = [
    "EmbeddingError",
    "SearchService",
    "WeaviateSearchError",
    "build_candidate_response",
    "make_code_preview",
]
