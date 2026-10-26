"""Shared test configuration and fixtures."""
import pytest

from app.services.workspace_manager import get_workspace_manager


@pytest.fixture(autouse=True)
def reset_workspace():
    """Reset workspace to default before and after each test."""
    manager = get_workspace_manager()
    manager.reset_to_default()
    yield
    manager.reset_to_default()