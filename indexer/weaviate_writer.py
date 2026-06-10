from __future__ import annotations

import logging

from common.models import CodeChunk, MetadataObject
from common.settings import Settings
from common.weaviate_client import connect_weaviate


LOGGER = logging.getLogger(__name__)


class WeaviateWriteError(RuntimeError):
    pass


class WeaviateWriter:
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

    def ensure_schema(self) -> None:
        self.ensure_code_schema()

    def ensure_code_schema(self) -> None:
        try:
            from weaviate.classes.config import Configure, DataType, Property, VectorDistances
        except ImportError as exc:
            raise WeaviateWriteError("weaviate-client is not installed") from exc

        if self.client.collections.exists(self.settings.weaviate_collection):
            return
        self.client.collections.create(
            self.settings.weaviate_collection,
            vector_config=Configure.Vectors.self_provided(
                name=self.settings.weaviate_vector_name,
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                ),
            ),
            properties=[
                Property(name="repo", data_type=DataType.TEXT),
                Property(name="branch", data_type=DataType.TEXT),
                Property(name="path", data_type=DataType.TEXT),
                Property(name="gitlab_url", data_type=DataType.TEXT),
                Property(name="module_name", data_type=DataType.TEXT),
                Property(name="object_name", data_type=DataType.TEXT),
                Property(name="object_type", data_type=DataType.TEXT),
                Property(name="symbol_name", data_type=DataType.TEXT),
                Property(name="symbol_type", data_type=DataType.TEXT),
                Property(name="start_line", data_type=DataType.INT),
                Property(name="end_line", data_type=DataType.INT),
                Property(name="code", data_type=DataType.TEXT),
                Property(name="identifiers", data_type=DataType.TEXT_ARRAY),
                Property(name="search_text", data_type=DataType.TEXT),
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="source_commit", data_type=DataType.TEXT),
                Property(name="indexed_at", data_type=DataType.DATE),
                Property(name="content_hash", data_type=DataType.TEXT),
            ],
        )

    def ensure_metadata_schema(self) -> None:
        try:
            from weaviate.classes.config import Configure, DataType, Property, VectorDistances
        except ImportError as exc:
            raise WeaviateWriteError("weaviate-client is not installed") from exc

        if self.client.collections.exists(self.settings.metadata_weaviate_collection):
            return
        self.client.collections.create(
            self.settings.metadata_weaviate_collection,
            vector_config=Configure.Vectors.self_provided(
                name=self.settings.metadata_weaviate_vector_name,
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE
                ),
            ),
            properties=[
                Property(name="repo", data_type=DataType.TEXT),
                Property(name="branch", data_type=DataType.TEXT),
                Property(name="path", data_type=DataType.TEXT),
                Property(name="object_name", data_type=DataType.TEXT),
                Property(name="object_type", data_type=DataType.TEXT),
                Property(name="synonym", data_type=DataType.TEXT),
                Property(name="comment", data_type=DataType.TEXT),
                Property(name="attributes", data_type=DataType.TEXT_ARRAY),
                Property(name="tabular_sections", data_type=DataType.TEXT_ARRAY),
                Property(name="forms", data_type=DataType.TEXT_ARRAY),
                Property(name="commands", data_type=DataType.TEXT_ARRAY),
                Property(name="related_bsl_paths", data_type=DataType.TEXT_ARRAY),
                Property(name="search_text", data_type=DataType.TEXT),
                Property(name="metadata_id", data_type=DataType.TEXT),
                Property(name="source_commit", data_type=DataType.TEXT),
                Property(name="indexed_at", data_type=DataType.DATE),
                Property(name="content_hash", data_type=DataType.TEXT),
            ],
        )

    def write_chunks(self, chunks: list[CodeChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise WeaviateWriteError("chunks and vectors length mismatch")
        if not chunks:
            return 0
        try:
            from weaviate.util import generate_uuid5
        except ImportError as exc:
            raise WeaviateWriteError("weaviate-client is not installed") from exc

        collection = self.client.collections.use(self.settings.weaviate_collection)
        with collection.batch.fixed_size(batch_size=self.settings.weaviate_batch_size) as batch:
            for chunk, vector in zip(chunks, vectors):
                batch.add_object(
                    properties=chunk.to_properties(),
                    uuid=generate_uuid5(chunk.chunk_id),
                    vector={self.settings.weaviate_vector_name: vector},
                )
        failed = collection.batch.failed_objects
        if failed:
            LOGGER.warning("failed to upload %s chunks; first failure=%s", len(failed), failed[0])
            raise WeaviateWriteError(f"failed to upload {len(failed)} chunks")
        return len(chunks)

    def write_metadata_objects(self, objects: list[MetadataObject], vectors: list[list[float]]) -> int:
        if len(objects) != len(vectors):
            raise WeaviateWriteError("metadata objects and vectors length mismatch")
        if not objects:
            return 0
        try:
            from weaviate.util import generate_uuid5
        except ImportError as exc:
            raise WeaviateWriteError("weaviate-client is not installed") from exc

        collection = self.client.collections.use(self.settings.metadata_weaviate_collection)
        with collection.batch.fixed_size(batch_size=self.settings.weaviate_batch_size) as batch:
            for metadata_object, vector in zip(objects, vectors):
                batch.add_object(
                    properties=metadata_object.to_properties(),
                    uuid=generate_uuid5(metadata_object.metadata_id),
                    vector={self.settings.metadata_weaviate_vector_name: vector},
                )
        failed = collection.batch.failed_objects
        if failed:
            LOGGER.warning("failed to upload %s metadata objects; first failure=%s", len(failed), failed[0])
            raise WeaviateWriteError(f"failed to upload {len(failed)} metadata objects")
        return len(objects)
