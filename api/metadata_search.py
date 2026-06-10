from __future__ import annotations

import logging

from api.search_models import MetadataCandidate
from api.weaviate_search import _metadata_score
from common.settings import Settings
from common.weaviate_client import connect_weaviate


LOGGER = logging.getLogger(__name__)


class MetadataSearchError(RuntimeError):
    pass


class MetadataSearch:
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
    ) -> list[MetadataCandidate]:
        try:
            from weaviate.classes.query import Filter, MetadataQuery
        except ImportError as exc:
            raise MetadataSearchError("weaviate-client is not installed") from exc

        try:
            collection = self.client.collections.use(self.settings.metadata_weaviate_collection)
            filters = Filter.by_property("repo").equal(repo) & Filter.by_property("branch").equal(branch)
            response = collection.query.hybrid(
                query=query,
                vector=query_vector,
                target_vector=self.settings.metadata_weaviate_vector_name,
                alpha=self.settings.metadata_search_alpha,
                filters=filters,
                query_properties=[
                    "search_text^3",
                    "object_name^3",
                    "synonym^2",
                    "comment",
                    "attributes",
                    "tabular_sections",
                    "forms",
                    "commands",
                    "related_bsl_paths",
                ],
                return_metadata=MetadataQuery(score=True),
                limit=limit,
            )
        except Exception as exc:
            LOGGER.error("metadata search unavailable: %s", exc)
            raise MetadataSearchError(f"metadata search unavailable: {exc}") from exc

        items: list[MetadataCandidate] = []
        total = len(response.objects)
        for rank, obj in enumerate(response.objects, start=1):
            items.append(
                MetadataCandidate.from_properties(
                    dict(obj.properties),
                    score=_metadata_score(obj.metadata, rank=rank, total=total),
                    original_rank=rank,
                )
            )
        return items
