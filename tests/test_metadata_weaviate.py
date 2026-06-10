import sys
import types
from pathlib import Path
from types import SimpleNamespace

from api.metadata_search import MetadataSearch
from common.models import MetadataObject
from common.settings import Settings
from indexer.weaviate_writer import WeaviateWriter


class FakeBatch:
    def __init__(self):
        self.failed_objects = []
        self.objects = []
        self.batch_size = None

    def fixed_size(self, batch_size):
        self.batch_size = batch_size
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_object(self, *, properties, uuid, vector):
        self.objects.append({"properties": properties, "uuid": uuid, "vector": vector})


class FakeCollection:
    def __init__(self):
        self.batch = FakeBatch()


class FakeCollections:
    def __init__(self, collection):
        self.collection = collection
        self.used_name = ""

    def use(self, name):
        self.used_name = name
        return self.collection


class FakeClient:
    def __init__(self, collection):
        self.collections = FakeCollections(collection)


def test_write_metadata_objects_uses_metadata_collection_and_vector(monkeypatch, tmp_path):
    install_fake_weaviate_util(monkeypatch)
    collection = FakeCollection()
    writer = WeaviateWriter(settings(tmp_path))
    writer._client = FakeClient(collection)

    count = writer.write_metadata_objects([metadata_object()], [[0.1, 0.2]])

    assert count == 1
    assert writer.client.collections.used_name == "OneCMetadataObject"
    stored = collection.batch.objects[0]
    assert stored["uuid"] == "uuid-meta-1"
    assert stored["vector"] == {"metadata_vector": [0.1, 0.2]}
    assert stored["properties"]["object_name"] == "Заявка"


def test_metadata_search_queries_metadata_collection(monkeypatch, tmp_path):
    install_fake_weaviate_query(monkeypatch)
    collection = FakeSearchCollection()
    search = MetadataSearch(settings(tmp_path))
    search._client = FakeClient(collection)

    results = search.search(
        query="температурный груз",
        query_vector=[0.1, 0.2],
        repo="gp",
        branch="master",
        limit=5,
    )

    assert search.client.collections.used_name == "OneCMetadataObject"
    assert collection.query.last_call["target_vector"] == "metadata_vector"
    assert collection.query.last_call["limit"] == 5
    assert results[0].object_name == "Заявка"
    assert results[0].related_bsl_paths == ["src/doc.bsl"]
    assert results[0].score == 0.7


class FakeSearchQuery:
    def __init__(self):
        self.last_call = {}

    def hybrid(self, **kwargs):
        self.last_call = kwargs
        return SimpleNamespace(
            objects=[
                SimpleNamespace(
                    properties={
                        "repo": "gp",
                        "branch": "master",
                        "path": "src/configuration/Documents/Заявка",
                        "object_name": "Заявка",
                        "object_type": "Document",
                        "synonym": "Заявка",
                        "comment": "",
                        "attributes": ["ТемпературныйРежим"],
                        "tabular_sections": [],
                        "forms": [],
                        "commands": [],
                        "related_bsl_paths": ["src/doc.bsl"],
                        "search_text": "Заявка",
                        "metadata_id": "meta-1",
                        "source_commit": "abc",
                        "indexed_at": "2026-06-10T00:00:00+00:00",
                        "content_hash": "hash",
                    },
                    metadata=SimpleNamespace(score=0.7),
                )
            ]
        )


class FakeSearchCollection:
    def __init__(self):
        self.query = FakeSearchQuery()


def install_fake_weaviate_util(monkeypatch):
    weaviate_module = types.ModuleType("weaviate")
    util_module = types.ModuleType("weaviate.util")
    util_module.generate_uuid5 = lambda value: f"uuid-{value}"
    monkeypatch.setitem(sys.modules, "weaviate", weaviate_module)
    monkeypatch.setitem(sys.modules, "weaviate.util", util_module)


def install_fake_weaviate_query(monkeypatch):
    install_fake_weaviate_util(monkeypatch)
    classes_module = types.ModuleType("weaviate.classes")
    query_module = types.ModuleType("weaviate.classes.query")
    query_module.Filter = FakeFilter
    query_module.MetadataQuery = lambda score=False: {"score": score}
    monkeypatch.setitem(sys.modules, "weaviate.classes", classes_module)
    monkeypatch.setitem(sys.modules, "weaviate.classes.query", query_module)


class FakeFilter:
    @classmethod
    def by_property(cls, name):
        return FakeFilterProperty(name)


class FakeFilterProperty:
    def __init__(self, name):
        self.name = name

    def equal(self, value):
        return FakeFilterExpression(self.name, value)


class FakeFilterExpression:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __and__(self, other):
        return self


def metadata_object() -> MetadataObject:
    return MetadataObject(
        repo="gp",
        branch="master",
        path="src/configuration/Documents/Заявка",
        object_name="Заявка",
        object_type="Document",
        synonym="Заявка",
        comment="",
        attributes=["ТемпературныйРежим"],
        tabular_sections=[],
        forms=[],
        commands=[],
        related_bsl_paths=["src/doc.bsl"],
        search_text="Заявка",
        metadata_id="meta-1",
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
        content_hash="hash",
    )


def settings(repo_path: Path) -> Settings:
    return Settings(
        repo_name="gp",
        repo_path=repo_path,
        branch="master",
        allowed_repos=["gp"],
        allowed_branches=["master"],
        gitlab_base_url="https://gitlab.company.ru",
        gitlab_project_path="group/project",
        weaviate_url="http://localhost:8080",
        weaviate_api_key=None,
        weaviate_grpc_host=None,
        weaviate_grpc_port=50051,
        weaviate_grpc_secure=False,
        weaviate_collection="OneCCodeChunk",
        weaviate_vector_name="code_vector",
        weaviate_batch_size=64,
        embeddings_base_url="http://localhost:8001/v1",
        embeddings_api_key="test-key",
        embeddings_model="qwen3-embedder-8b",
        embedding_batch_size=16,
        embedding_text_limit=16000,
        embedding_timeout_seconds=30,
        embedding_retries=3,
        llm_query_expansion_enabled=False,
        llm_base_url="http://localhost:8002/v1",
        llm_api_key="test-key",
        llm_model="qwen2.5-coder-32b-instruct",
        llm_timeout_seconds=10,
        llm_retries=1,
        llm_max_tokens=512,
        search_alpha=0.35,
        search_internal_limit=50,
        search_internal_limit_max=200,
        indexer_fail_on_failed_files=True,
        api_default_limit=10,
        api_max_limit=50,
        api_host="0.0.0.0",
        api_port=8000,
    )
