"""Authentication service - user auth and JWT management."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import settings
from packages.db.repositories.user import UserRepository
from packages.db.repositories.organization import OrganizationRepository
from packages.db.models import UserModel, OrganizationModel


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"


class TokenData(BaseModel):
    """Data encoded in JWT token."""

    user_id: str
    organization_id: str
    email: str
    role: str
    exp: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthService:
    """
    Service for authentication and authorization.

    Handles:
    - User registration and login
    - Password hashing and verification
    - JWT token generation and validation
    - Organization context
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.org_repo = OrganizationRepository(session)

    # === Password Management ===

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # === User Registration ===

    async def register_organization(
        self,
        *,
        org_name: str,
        admin_email: str,
        admin_password: str,
        admin_name: str,
        license_number: str | None = None,
        state: str = "FL",
    ) -> tuple[OrganizationModel, UserModel]:
        """
        Register a new organization with admin user.

        Creates organization and first admin user in a single transaction.
        """
        # Check if email already exists
        existing = await self.user_repo.get_by_email(admin_email)
        if existing:
            raise ValueError("Email already registered")

        # Create organization
        org = await self.org_repo.create(
            id=uuid4(),
            name=org_name,
            license_number=license_number,
            state=state,
            subscription_tier="starter",
            subscription_status="active",
        )

        # Create admin user
        user = await self.user_repo.create(
            id=uuid4(),
            organization_id=org.id,
            email=admin_email.lower(),
            hashed_password=self.hash_password(admin_password),
            full_name=admin_name,
            role="admin",
            is_active=True,
        )

        return org, user

    async def register_user(
        self,
        *,
        organization_id: UUID,
        email: str,
        password: str,
        full_name: str,
        role: str = "agent",
        phone: str | None = None,
        license_number: str | None = None,
    ) -> UserModel:
        """
        Register a new user in an existing organization.

        Called by org admins to add team members.
        """
        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        # Verify organization exists
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise ValueError("Organization not found")

        return await self.user_repo.create(
            id=uuid4(),
            organization_id=organization_id,
            email=email.lower(),
            hashed_password=self.hash_password(password),
            full_name=full_name,
            role=role,
            phone=phone,
            license_number=license_number,
            is_active=True,
        )

    # === Authentication ===

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> UserModel | None:
        """
        Authenticate user with email and password.

        Returns user if valid, None otherwise.
        """
        user = await self.user_repo.get_by_email(email.lower())

        if not user:
            return None

        if not user.is_active:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        # Update last login
        await self.user_repo.update_last_login(user.id)

        return user

    async def login(
        self,
        email: str,
        password: str,
    ) -> TokenPair | None:
        """
        Login and return token pair.

        Returns None if authentication fails.
        """
        user = await self.authenticate(email, password)

        if not user:
            return None

        return self.create_token_pair(user)

    # === Token Management ===

    def create_token_pair(self, user: UserModel) -> TokenPair:
        """Create access and refresh token pair for user."""
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    def _create_access_token(self, user: UserModel) -> str:
        """Create JWT access token."""
        expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        payload = {
            "sub": str(user.id),
            "org": str(user.organization_id),
            "email": user.email,
            "role": user.role,
            "type": "access",
            "exp": expires,
        }

        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    def _create_refresh_token(self, user: UserModel) -> str:
        """Create JWT refresh token."""
        expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": expires,
        }

        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    async def refresh_tokens(self, refresh_token: str) -> TokenPair | None:
        """
        Create new token pair from refresh token.

        Returns None if refresh token is invalid.
        """
        payload = self.decode_token(refresh_token)

        if not payload:
            return None

        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            return None

        return self.create_token_pair(user)

    async def get_current_user(self, token: str) -> UserModel | None:
        """
        Get current user from access token.

        Returns None if token is invalid or user not found.
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            return None

        return user

    # === Password Reset ===

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user's password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False

        if not self.verify_password(current_password, user.hashed_password):
            return False

        await self.user_repo.update(
            user_id,
            hashed_password=self.hash_password(new_password),
        )

        return True

    def create_password_reset_token(self, user: UserModel) -> str:
        """Create a password reset token valid for 1 hour."""
        expires = datetime.utcnow() + timedelta(hours=1)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "password_reset",
            "exp": expires,
        }

        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    async def request_password_reset(self, email: str) -> tuple[UserModel, str] | None:
        """
        Request a password reset for an email.

        Returns user and reset token if email exists, None otherwise.
        Always returns quickly to prevent email enumeration.
        """
        user = await self.user_repo.get_by_email(email.lower())

        if not user or not user.is_active:
            return None

        token = self.create_password_reset_token(user)
        return user, token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using a valid reset token.

        Returns True if successful, False if token invalid or expired.
        """
        payload = self.decode_token(token)

        if not payload:
            return False

        if payload.get("type") != "password_reset":
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            return False

        # Verify email matches (extra security check)
        if user.email != payload.get("email"):
            return False

        await self.user_repo.update(
            user.id,
            hashed_password=self.hash_password(new_password),
        )

        return True

    async def validate_reset_token(self, token: str) -> UserModel | None:
        """
        Validate a password reset token and return the associated user.

        Returns None if token is invalid.
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        if payload.get("type") != "password_reset":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            return None

        return user
