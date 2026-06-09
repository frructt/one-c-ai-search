from pathlib import Path

from api.search_models import SearchCandidate
from api.search_service import SearchService
from common.settings import Settings


class FakeEmbedder:
    def __init__(self):
        self.texts = []

    def embed(self, text):
        self.texts.append(text)
        return [0.1, 0.2]

    def close(self):
        pass


class FakeSearchBackend:
    def __init__(self, by_profile):
        self.by_profile = by_profile
        self.calls = []

    def search(self, *, query, query_vector, repo, branch, limit, profile):
        self.calls.append(
            {
                "query": query,
                "query_vector": query_vector,
                "repo": repo,
                "branch": branch,
                "limit": limit,
                "profile": profile.name,
            }
        )
        return self.by_profile.get(profile.name, [])

    def close(self):
        pass


def test_search_service_uses_multiple_profiles_and_ranks_files():
    right_a = candidate(
        path="src/CommonModules/ТемпературныеГрузы/Ext/Module.bsl",
        symbol_name="Рассчитать",
        identifiers=["ТемпературныйРежим"],
        score=0.72,
        chunk_id="right-a",
        retrieval_profiles=("keyword",),
        original_rank=2,
    )
    right_b = candidate(
        path="src/CommonModules/ТемпературныеГрузы/Ext/Module.bsl",
        symbol_name="Заполнить",
        identifiers=["ТемпературныйРежим"],
        score=0.70,
        chunk_id="right-b",
        retrieval_profiles=("metadata",),
        original_rank=1,
    )
    decoy = candidate(
        path="src/CommonModules/ОбщиеТарифы/Ext/Module.bsl",
        symbol_name="РассчитатьТариф",
        identifiers=["Тариф"],
        score=0.90,
        chunk_id="decoy",
        retrieval_profiles=("balanced",),
        original_rank=1,
    )
    backend = FakeSearchBackend(
        {
            "balanced": [decoy],
            "keyword": [right_a],
            "metadata": [right_b],
            "vector": [],
        }
    )
    service = SearchService(
        settings(),
        embedder=FakeEmbedder(),
        llm_expander=None,
        search_backend=backend,
    )

    response = service.find_change_places(
        query="Нужно изменить температурный груз",
        repo="gp",
        branch="master",
        limit=10,
    )

    assert {call["profile"] for call in backend.calls} == {
        "balanced",
        "keyword",
        "metadata",
        "vector",
    }
    assert response.candidates[0].path == "src/CommonModules/ТемпературныеГрузы/Ext/Module.bsl"
    assert len(response.candidates) == 2


def test_search_service_deduplicates_chunks_across_profiles():
    lower_score = candidate(
        path="src/CommonModules/Расчет/Ext/Module.bsl",
        symbol_name="Рассчитать",
        score=0.55,
        chunk_id="same",
        retrieval_profiles=("balanced",),
        original_rank=2,
    )
    higher_score = candidate(
        path="src/CommonModules/Расчет/Ext/Module.bsl",
        symbol_name="Рассчитать",
        score=0.80,
        chunk_id="same",
        retrieval_profiles=("keyword",),
        original_rank=1,
    )
    backend = FakeSearchBackend(
        {
            "balanced": [lower_score],
            "keyword": [higher_score],
            "metadata": [],
            "vector": [],
        }
    )
    service = SearchService(
        settings(),
        embedder=FakeEmbedder(),
        llm_expander=None,
        search_backend=backend,
    )

    response = service.find_change_places(
        query="Рассчитать",
        repo="gp",
        branch="master",
        limit=10,
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].score == 0.80


def candidate(
    *,
    path: str,
    symbol_name: str,
    score: float,
    chunk_id: str,
    retrieval_profiles: tuple[str, ...],
    original_rank: int,
    identifiers: list[str] | None = None,
) -> SearchCandidate:
    return SearchCandidate(
        repo="gp",
        branch="master",
        path=path,
        gitlab_url=f"https://gitlab/{path}",
        module_name=path.split("/")[-3],
        object_name=path.split("/")[-3],
        object_type="CommonModule",
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=1,
        end_line=5,
        code=f"Функция {symbol_name}()\nКонецФункции",
        identifiers=identifiers or [],
        search_text=symbol_name,
        chunk_id=chunk_id,
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
        content_hash=chunk_id,
        score=score,
        final_score=score,
        retrieval_profiles=retrieval_profiles,
        original_rank=original_rank,
    )


def settings() -> Settings:
    return Settings(
        repo_name="gp",
        repo_path=Path("/tmp/gp_bsl"),
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
