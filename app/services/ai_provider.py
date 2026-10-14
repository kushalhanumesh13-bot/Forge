from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_ENDPOINTS = {
    "ollama": DEFAULT_OLLAMA_ENDPOINT,
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
}
SUPPORTED_PROVIDERS = {
    "ollama": "Ollama",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}


class ProviderConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    endpoint: str
    api_key: str | None = None

    @property
    def api_key_configured(self) -> bool:
        return bool(self.api_key)

    def public(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_name": SUPPORTED_PROVIDERS[self.provider],
            "model": self.model,
            "endpoint": self.endpoint,
            "api_key_configured": self.api_key_configured,
        }


class ProviderConfigStore:
    def __init__(self, root: Path):
        self.path = root / ".forge" / "ai-providers.json"

    def load(self) -> ProviderConfig | None:
        if not self.path.is_file():
            return None

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProviderConfigurationError(
                "The saved AI provider configuration could not be read."
            ) from error

        if not isinstance(data, dict):
            raise ProviderConfigurationError(
                "The saved AI provider configuration is invalid."
            )

        return ProviderConfig(
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            endpoint=data.get("endpoint", ""),
            api_key=data.get("api_key") or None,
        )

    def save(self, config: ProviderConfig) -> None:
        directory = self.path.parent
        directory.mkdir(mode=0o700, exist_ok=True)
        try:
            os.chmod(directory, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        except OSError:
            pass

        payload = json.dumps(
            {
                "provider": config.provider,
                "model": config.model,
                "endpoint": config.endpoint,
                "api_key": config.api_key,
            },
            indent=2,
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="ai-providers-",
            suffix=".tmp",
            dir=directory,
            text=True,
        )
        try:
            os.chmod(
                temporary_name,
                stat.S_IRUSR | stat.S_IWUSR,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
            try:
                os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
        except OSError:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise

    def remove(self) -> bool:
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return False


def validate_config(
    provider: str,
    model: str,
    endpoint: str | None,
    api_key: str | None,
) -> ProviderConfig:
    if provider not in SUPPORTED_PROVIDERS:
        raise ProviderConfigurationError("Choose a supported AI provider.")

    if not isinstance(model, str) or not model.strip() or len(model) > 200:
        raise ProviderConfigurationError(
            "Model name must be between 1 and 200 characters."
        )
    if any(ord(character) < 32 for character in model):
        raise ProviderConfigurationError("Model name contains invalid characters.")

    selected_endpoint = endpoint or DEFAULT_ENDPOINTS[provider]
    parts = urlsplit(selected_endpoint)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ProviderConfigurationError("Endpoint must be a valid HTTP or HTTPS URL.")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ProviderConfigurationError(
            "Endpoint must not contain credentials, queries, or fragments."
        )
    try:
        parts.port
    except ValueError as error:
        raise ProviderConfigurationError("Endpoint contains an invalid port.") from error

    if provider == "ollama" and parts.hostname.lower() not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ProviderConfigurationError(
            "Ollama endpoints must stay on the local machine."
        )

    if api_key is not None and len(api_key) > 4096:
        raise ProviderConfigurationError("API key is too long.")

    return ProviderConfig(
        provider=provider,
        model=model.strip(),
        endpoint=selected_endpoint.rstrip("/"),
        api_key=api_key or None,
    )


def test_connection(config: ProviderConfig) -> dict[str, str | bool]:
    if config.provider != "ollama":
        return {
            "success": False,
            "status": "unsupported",
            "message": (
                "Connection testing for hosted providers is not enabled yet. "
                "Your configuration was saved without sending the key."
            ),
        }

    request = Request(
        f"{config.endpoint}/api/tags",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {401, 403}:
            return {
                "success": False,
                "status": "authentication_failed",
                "message": "Ollama rejected the connection.",
            }
        return {
            "success": False,
            "status": "unavailable",
            "message": f"Ollama returned HTTP {error.code}.",
        }
    except (URLError, TimeoutError, OSError):
        return {
            "success": False,
            "status": "unavailable",
            "message": "Ollama is unavailable at the configured local endpoint.",
        }
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return {
            "success": False,
            "status": "malformed_response",
            "message": "Ollama returned a malformed response.",
        }

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return {
            "success": False,
            "status": "malformed_response",
            "message": "Ollama returned no usable model list.",
        }

    names = {
        item.get("name")
        for item in models
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if config.model not in names:
        return {
            "success": False,
            "status": "missing_model",
            "message": f"Model '{config.model}' is not available in Ollama.",
        }

    return {
        "success": True,
        "status": "connected",
        "message": f"Ollama is reachable and '{config.model}' is available.",
    }
