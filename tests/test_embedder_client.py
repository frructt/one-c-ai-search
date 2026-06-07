import pytest

from indexer.embedder_client import EmbeddingClient, EmbeddingError


class FakeEmbeddings:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeOpenAIClient:
    def __init__(self, responses):
        self.embeddings = FakeEmbeddings(responses)


def test_embed_batch_parses_openai_compatible_response():
    sdk_client = FakeOpenAIClient(
        [
            {
                "data": [
                    {"index": 1, "embedding": [0.2, 0.3]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            }
        ]
    )

    client = EmbeddingClient(
        base_url="http://embedder/v1",
        api_key="test-key",
        model="qwen3-embedder-8b",
        client=sdk_client,
    )

    assert client.embed_batch(["a", "b"]) == [[0.1, 0.2], [0.2, 0.3]]
    assert sdk_client.embeddings.calls == [
        {"model": "qwen3-embedder-8b", "input": ["a", "b"]}
    ]


def test_embedder_retries_invalid_sdk_response():
    sdk_client = FakeOpenAIClient(
        [
            {"data": []},
            {"data": [{"index": 0, "embedding": [0.1]}]},
        ]
    )

    client = EmbeddingClient(
        base_url="http://embedder/v1",
        api_key="test-key",
        model="qwen3-embedder-8b",
        retries=2,
        client=sdk_client,
    )

    assert client.embed("x") == [0.1]
    assert len(sdk_client.embeddings.calls) == 2


def test_embedder_raises_clear_error_on_invalid_response():
    sdk_client = FakeOpenAIClient([{"data": []}])

    client = EmbeddingClient(
        base_url="http://embedder/v1",
        api_key="test-key",
        model="qwen3-embedder-8b",
        retries=1,
        client=sdk_client,
    )

    with pytest.raises(EmbeddingError, match="embedding endpoint unavailable"):
        client.embed("x")
