"""
Pytest configuration and fixtures for Airport backend tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
os.environ["STORAGE_ENDPOINT"] = "http://localhost:9000"
os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["STORAGE_BUCKET"] = "test-documents"

from packages.db.models import Base
from packages.db.session import get_db
from services.api.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_org_and_user(db_session: AsyncSession) -> dict:
    """Create a test organization and user."""
    from packages.db.models import OrganizationModel, UserModel
    from packages.core.services.auth import AuthService

    auth_service = AuthService()

    # Create organization
    org = OrganizationModel(
        name="Test Brokerage",
        settings={"state": "FL"}
    )
    db_session.add(org)
    await db_session.flush()

    # Create user
    password_hash = auth_service.hash_password("testpassword123")
    user = UserModel(
        organization_id=org.id,
        email="test@example.com",
        hashed_password=password_hash,
        full_name="Test User",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "organization": org,
        "user": user,
        "password": "testpassword123",
    }


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient, test_org_and_user: dict) -> dict:
    """Get authentication headers for API requests."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_org_and_user["user"].email,
            "password": test_org_and_user["password"],
        }
    )

    assert response.status_code == 200, f"Login failed: {response.json()}"
    tokens = response.json()

    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def test_transaction(
    db_session: AsyncSession,
    test_org_and_user: dict
) -> dict:
    """Create a test transaction."""
    from packages.db.models import TransactionModel
    from datetime import date
    from decimal import Decimal

    transaction = TransactionModel(
        organization_id=test_org_and_user["organization"].id,
        created_by=test_org_and_user["user"].id,
        property_address={
            "street": "123 Test St",
            "city": "Miami",
            "state": "FL",
            "zip_code": "33101"
        },
        transaction_type="purchase",
        status="under_contract",
        purchase_price=Decimal("500000"),
        closing_date=date(2025, 2, 15),
        parties=[
            {"role": "buyer", "name": "John Buyer"},
            {"role": "seller", "name": "Jane Seller"},
        ],
    )
    db_session.add(transaction)
    await db_session.commit()

    return {"transaction": transaction}
