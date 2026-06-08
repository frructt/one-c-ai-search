from __future__ import annotations

import logging

from common.settings import Settings
from common.weaviate_client import connect_weaviate


LOGGER = logging.getLogger(__name__)


class WeaviateSearchError(RuntimeError):
    pass


class WeaviateSearch:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = connect_weaviate(self.settings)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def search(
        self,
        *,
        query: str,
        query_vector: list[float],
        repo: str,
        branch: str,
        limit: int,
    ) -> list[dict]:
        try:
            from weaviate.classes.query import Filter, MetadataQuery
        except ImportError as exc:
            raise WeaviateSearchError("weaviate-client is not installed") from exc

        try:
            collection = self.client.collections.use(self.settings.weaviate_collection)
            filters = Filter.by_property("repo").equal(repo) & Filter.by_property("branch").equal(branch)
            response = collection.query.hybrid(
                query=query,
                vector=query_vector,
                target_vector=self.settings.weaviate_vector_name,
                alpha=self.settings.search_alpha,
                filters=filters,
                query_properties=[
                    "search_text^3",
                    "symbol_name^2",
                    "module_name^2",
                    "identifiers",
                    "path",
                ],
                return_metadata=MetadataQuery(score=True),
                limit=limit,
            )
        except Exception as exc:
            LOGGER.error("Weaviate unavailable: %s", exc)
            raise WeaviateSearchError(f"Weaviate unavailable: {exc}") from exc

        items: list[dict] = []
        total = len(response.objects)
        for rank, obj in enumerate(response.objects, start=1):
            item = dict(obj.properties)
            item["score"] = _metadata_score(obj.metadata, rank=rank, total=total)
            items.append(item)
        return items


def _metadata_score(metadata, *, rank: int, total: int) -> float:
    raw_score = getattr(metadata, "score", None) if metadata is not None else None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return _rank_fallback_score(rank=rank, total=total)
    if score > 0:
        return score
    return _rank_fallback_score(rank=rank, total=total)


def _rank_fallback_score(*, rank: int, total: int) -> float:
    safe_rank = max(1, rank)
    safe_total = max(1, total, safe_rank)
    if safe_total == 1:
        return 1.0
    position = (safe_rank - 1) / (safe_total - 1)
    return round(max(0.01, 1.0 - position * 0.99), 6)
