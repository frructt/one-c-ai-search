from pathlib import Path

from common.settings import Settings
from indexer import build_index
from indexer.bsl_indexer import BslIndexStats
from indexer.metadata_indexer import MetadataIndexStats


class FakeEmbedder:
    def close(self):
        pass


class FakeWriter:
    def __init__(self, settings):
        self.settings = settings

    def ensure_code_schema(self):
        pass

    def ensure_metadata_schema(self):
        pass

    def close(self):
        pass


def test_full_build_index_runs_bsl_then_metadata(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    (repo_path / "src").mkdir(parents=True)
    calls = []

    def fake_index_bsl(**kwargs):
        calls.append("bsl")
        return BslIndexStats()

    def fake_index_metadata(**kwargs):
        calls.append("metadata")
        return MetadataIndexStats()

    monkeypatch.setattr(build_index, "load_settings", lambda: settings(repo_path))
    monkeypatch.setattr(build_index, "current_commit", lambda path: "abc")
    monkeypatch.setattr(build_index, "make_embedder", lambda settings: FakeEmbedder())
    monkeypatch.setattr(build_index, "WeaviateWriter", FakeWriter)
    monkeypatch.setattr(build_index, "index_bsl", fake_index_bsl)
    monkeypatch.setattr(build_index, "index_metadata", fake_index_metadata)
    monkeypatch.setattr(build_index, "print_stats", lambda stats: None)
    monkeypatch.setattr(build_index, "print_metadata_stats", lambda stats: None)

    exit_code = build_index.main()

    assert exit_code == 0
    assert calls == ["bsl", "metadata"]


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
