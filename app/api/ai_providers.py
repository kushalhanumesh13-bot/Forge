from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.ai_provider import (
    ProviderConfigStore,
    ProviderConfigurationError,
    SUPPORTED_PROVIDERS,
    test_connection,
    validate_config,
)
from app.api.workspace import ROOT


router = APIRouter(prefix="/api/ai/providers", tags=["ai-providers"])
store = ProviderConfigStore(ROOT)
_LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost", "testclient"}


class ProviderConfigRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(min_length=1, max_length=200)
    endpoint: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=4096)


def _require_local(request: Request) -> None:
    client = request.client
    if client and client.host.lower() not in _LOCAL_CLIENTS:
        raise HTTPException(
            status_code=403,
            detail="AI provider settings are available only from the local machine.",
        )


def _read_config():
    try:
        return store.load()
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("")
def get_provider_config(request: Request):
    _require_local(request)
    config = _read_config()
    return {
        "providers": [
            {"id": provider_id, "name": name}
            for provider_id, name in SUPPORTED_PROVIDERS.items()
        ],
        "config": config.public() if config else None,
    }


@router.put("")
def save_provider_config(request: Request, payload: ProviderConfigRequest):
    _require_local(request)
    existing = _read_config()
    api_key = payload.api_key
    if api_key is None and existing and existing.provider == payload.provider:
        api_key = existing.api_key

    try:
        config = validate_config(
            payload.provider,
            payload.model,
            payload.endpoint,
            api_key,
        )
        store.save(config)
    except ProviderConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The AI provider configuration could not be saved.",
        ) from error

    return {"config": config.public(), "message": "Provider configuration saved."}


@router.delete("")
def remove_provider_config(request: Request):
    _require_local(request)
    try:
        removed = store.remove()
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The AI provider configuration could not be removed.",
        ) from error
    return {
        "removed": removed,
        "config": None,
        "message": "Provider configuration removed." if removed else "No provider configuration was saved.",
    }


@router.post("/test")
def test_provider_config(request: Request):
    _require_local(request)
    config = _read_config()
    if config is None:
        raise HTTPException(
            status_code=400,
            detail="Save a provider configuration before testing the connection.",
        )
    return test_connection(config)
