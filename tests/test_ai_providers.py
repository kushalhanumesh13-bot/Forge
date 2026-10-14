import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api.ai_providers as ai_api
import app.services.ai_provider as provider_service
from app.main import app
from app.services.ai_provider import ProviderConfigStore, validate_config


client = TestClient(app)


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ai_api, "store", ProviderConfigStore(tmp_path))
    return ai_api.store


def test_provider_config_is_empty_without_saved_secret(isolated_store):
    response = client.get("/api/ai/providers")

    assert response.status_code == 200
    assert response.json()["config"] is None


def test_save_update_and_remove_masks_api_key(isolated_store):
    save = client.put(
        "/api/ai/providers",
        json={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "endpoint": "https://api.openai.com/v1",
            "api_key": "sk-secret-value",
        },
    )
    assert save.status_code == 200
    assert save.json()["config"]["api_key_configured"] is True
    assert "sk-secret-value" not in save.text

    update = client.put(
        "/api/ai/providers",
        json={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "endpoint": "https://api.openai.com/v1",
        },
    )
    assert update.status_code == 200
    assert update.json()["config"]["model"] == "gpt-4.1-mini"
    assert update.json()["config"]["api_key_configured"] is True
    assert "sk-secret-value" not in update.text

    stored = isolated_store.path.read_text(encoding="utf-8")
    assert "sk-secret-value" in stored

    read = client.get("/api/ai/providers")
    assert read.json()["config"]["api_key_configured"] is True
    assert "sk-secret-value" not in read.text

    removed = client.delete("/api/ai/providers")
    assert removed.status_code == 200
    assert removed.json()["config"] is None
    assert not isolated_store.path.exists()


def test_invalid_provider_and_remote_ollama_endpoint_are_rejected(isolated_store):
    invalid_provider = client.put(
        "/api/ai/providers",
        json={"provider": "unknown", "model": "model"},
    )
    assert invalid_provider.status_code == 422

    remote_ollama = client.put(
        "/api/ai/providers",
        json={
            "provider": "ollama",
            "model": "llama3.2",
            "endpoint": "http://192.168.1.20:11434",
        },
    )
    assert remote_ollama.status_code == 422
    assert not isolated_store.path.exists()


def test_ollama_connection_success_and_missing_model(isolated_store, monkeypatch):
    client.put(
        "/api/ai/providers",
        json={"provider": "ollama", "model": "llama3.2"},
    )

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    monkeypatch.setattr(
        provider_service,
        "urlopen",
        lambda request, timeout: Response(
            json.dumps({"models": [{"name": "llama3.2"}]}).encode()
        ),
    )
    connected = client.post("/api/ai/providers/test")
    assert connected.json() == {
        "success": True,
        "status": "connected",
        "message": "Ollama is reachable and 'llama3.2' is available.",
    }

    monkeypatch.setattr(
        provider_service,
        "urlopen",
        lambda request, timeout: Response(
            json.dumps({"models": [{"name": "other"}]}).encode()
        ),
    )
    missing = client.post("/api/ai/providers/test")
    assert missing.json()["status"] == "missing_model"
    assert missing.json()["success"] is False


def test_ollama_connection_unavailable_is_reported(isolated_store, monkeypatch):
    client.put(
        "/api/ai/providers",
        json={"provider": "ollama", "model": "llama3.2"},
    )

    def unavailable(*_args, **_kwargs):
        raise provider_service.URLError("offline")

    monkeypatch.setattr(provider_service, "urlopen", unavailable)
    response = client.post("/api/ai/providers/test")

    assert response.json()["status"] == "unavailable"
    assert response.json()["success"] is False


def test_hosted_connection_test_does_not_send_saved_key(isolated_store, monkeypatch):
    client.put(
        "/api/ai/providers",
        json={
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "api_key": "anthropic-secret",
        },
    )
    monkeypatch.setattr(
        provider_service,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("Hosted provider must not make a request"),
    )

    response = client.post("/api/ai/providers/test")

    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"
    assert "anthropic-secret" not in response.text


def test_validate_config_rejects_endpoint_credentials():
    with pytest.raises(ValueError):
        validate_config(
            "openai",
            "model",
            "https://user:password@example.com/v1",
            None,
        )
