import httpx
import pytest

from indexer.embedder_client import EmbeddingClient, EmbeddingError


def test_embed_batch_parses_openai_compatible_response():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read()
        assert b"qwen3-embedder-8b" in payload
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.2, 0.3]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    client = EmbeddingClient(
        base_url="http://embedder/v1",
        model="qwen3-embedder-8b",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.embed_batch(["a", "b"]) == [[0.1, 0.2], [0.2, 0.3]]


def test_embedder_retries_server_errors():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(500, json={"error": "down"})
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1]}]})

    client = EmbeddingClient(
        base_url="http://embedder/v1",
        model="qwen3-embedder-8b",
        retries=2,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.embed("x") == [0.1]
    assert calls["count"] == 2


def test_embedder_raises_clear_error_on_invalid_response():
    client = EmbeddingClient(
        base_url="http://embedder/v1",
        model="qwen3-embedder-8b",
        retries=1,
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": []}))
        ),
    )

    with pytest.raises(EmbeddingError, match="embedding endpoint unavailable"):
        client.embed("x")
