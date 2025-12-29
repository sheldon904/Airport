"""Pytest configuration and shared fixtures."""

import pytest
from uuid import uuid4


@pytest.fixture
def sample_transaction_id():
    """Generate a sample transaction ID."""
    return uuid4()


@pytest.fixture
def sample_organization_id():
    """Generate a sample organization ID."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return uuid4()
