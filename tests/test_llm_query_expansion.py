import pytest

from api.llm_query_expansion import LlmClient, LlmError, expand_query_for_search


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeChat:
    def __init__(self, responses):
        self.completions = FakeCompletions(responses)


class FakeOpenAIClient:
    def __init__(self, responses):
        self.chat = FakeChat(responses)


def test_llm_expansion_uses_chat_completions():
    sdk_client = FakeOpenAIClient(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": "Нужно поменять расчет тарифа\nстоимость ставка цена"
                        }
                    }
                ]
            }
        ]
    )
    client = LlmClient(
        base_url="http://llm/v1",
        api_key="test-key",
        model="qwen-coder",
        client=sdk_client,
    )

    expanded = client.expand_query("Нужно поменять расчет тарифа")

    assert "стоимость" in expanded
    assert sdk_client.chat.completions.calls[0]["model"] == "qwen-coder"
    assert sdk_client.chat.completions.calls[0]["temperature"] == 0


def test_llm_expansion_preserves_original_query_when_model_omits_it():
    sdk_client = FakeOpenAIClient(
        [{"choices": [{"message": {"content": "стоимость ставка цена"}}]}]
    )
    client = LlmClient(
        base_url="http://llm/v1",
        api_key="test-key",
        model="qwen-coder",
        client=sdk_client,
    )

    expanded = client.expand_query("Нужно поменять расчет тарифа")

    assert expanded.startswith("Нужно поменять расчет тарифа")
    assert "Дополнение LLM: стоимость ставка цена" in expanded


def test_llm_expansion_raises_on_empty_response():
    sdk_client = FakeOpenAIClient([{"choices": [{"message": {"content": ""}}]}])
    client = LlmClient(
        base_url="http://llm/v1",
        api_key="test-key",
        model="qwen-coder",
        client=sdk_client,
    )

    with pytest.raises(LlmError, match="LLM endpoint unavailable"):
        client.expand_query("Нужно поменять расчет тарифа")


def test_llm_expansion_falls_back_to_dictionary_expansion():
    class BrokenLlm:
        def expand_query(self, query):
            raise LlmError("down")

    expanded = expand_query_for_search(
        "Нужно поменять расчет тарифа для температурного груза",
        BrokenLlm(),
    )

    assert "стоимость" in expanded
    assert "рефрижератор" in expanded
