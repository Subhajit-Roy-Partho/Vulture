from __future__ import annotations

from types import SimpleNamespace

import pytest

from vulture.llm.providers import LLMProvider, ProviderConfig


class DummyAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class FakeResponsePayload:
    def __init__(self, *, output_text: str = "", raw: dict | None = None):
        self.output_text = output_text
        self._raw = raw or {}

    def model_dump(self) -> dict:
        return self._raw


class FakeChatPayload:
    def __init__(self, *, content: str, raw: dict | None = None):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
        self._raw = raw or {}

    def model_dump(self) -> dict:
        return self._raw


class FakeResponsesAPI:
    def __init__(self, fn):
        self._fn = fn

    def create(self, **kwargs):
        return self._fn(**kwargs)


class FakeChatCompletionsAPI:
    def __init__(self, fn):
        self._fn = fn

    def create(self, **kwargs):
        return self._fn(**kwargs)


class FakeChatAPI:
    def __init__(self, fn):
        self.completions = FakeChatCompletionsAPI(fn)


class FakeClient:
    def __init__(self, *, responses_fn, chat_fn):
        self.responses = FakeResponsesAPI(responses_fn)
        self.chat = FakeChatAPI(chat_fn)


def _provider_with_fake_client(fake_client: FakeClient) -> LLMProvider:
    provider = LLMProvider(
        ProviderConfig(
            name="openai",
            base_url="http://localhost:9999/v1",
            api_key="dummy",
            timeout_sec=5,
        )
    )
    provider.client = fake_client
    return provider


def test_complete_text_uses_responses_when_available() -> None:
    chat_called = {"value": False}

    def responses_fn(**kwargs):
        return FakeResponsePayload(output_text="RESP_OK", raw={"id": "resp_1"})

    def chat_fn(**kwargs):
        chat_called["value"] = True
        return FakeChatPayload(content="CHAT_OK", raw={"id": "chat_1"})

    provider = _provider_with_fake_client(FakeClient(responses_fn=responses_fn, chat_fn=chat_fn))
    result = provider.complete_text(model="gpt-5.2-xhigh", prompt="ping")

    assert result.content == "RESP_OK"
    assert result.raw["api_path"] == "responses"
    assert chat_called["value"] is False


def test_complete_text_falls_back_to_chat_on_responses_not_found() -> None:
    def responses_fn(**kwargs):
        raise DummyAPIError("Not found", status_code=404)

    def chat_fn(**kwargs):
        return FakeChatPayload(content="CHAT_OK", raw={"id": "chat_1"})

    provider = _provider_with_fake_client(FakeClient(responses_fn=responses_fn, chat_fn=chat_fn))
    result = provider.complete_text(model="gpt-5.2-xhigh", prompt="ping")

    assert result.content == "CHAT_OK"
    assert result.raw["api_path"] == "chat_completions"


def test_complete_text_raises_when_fallback_path_also_fails() -> None:
    def responses_fn(**kwargs):
        raise DummyAPIError("Not found", status_code=404)

    def chat_fn(**kwargs):
        raise RuntimeError("chat path failed")

    provider = _provider_with_fake_client(FakeClient(responses_fn=responses_fn, chat_fn=chat_fn))
    with pytest.raises(RuntimeError, match="chat path failed"):
        provider.complete_text(model="gpt-5.2-xhigh", prompt="ping")


def test_complete_json_parses_chat_fallback_payload() -> None:
    def responses_fn(**kwargs):
        raise DummyAPIError("Not found", status_code=404)

    def chat_fn(**kwargs):
        return FakeChatPayload(content='{"status":"ok","source":"chat"}', raw={"id": "chat_2"})

    provider = _provider_with_fake_client(FakeClient(responses_fn=responses_fn, chat_fn=chat_fn))
    payload = provider.complete_json(model="gpt-5.2-xhigh", prompt="json please")

    assert payload == {"status": "ok", "source": "chat"}
