"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from services.api.dependencies import AuthServiceDep, CurrentUserDep

router = APIRouter()


# === Request/Response Models ===


class RegisterOrganizationRequest(BaseModel):
    """Request to register a new organization."""

    organization_name: str
    admin_email: EmailStr
    admin_password: str
    admin_name: str
    license_number: str | None = None
    state: str = "FL"


class RegisterUserRequest(BaseModel):
    """Request to register a new user in an organization."""

    email: EmailStr
    password: str
    full_name: str
    role: str = "agent"
    phone: str | None = None
    license_number: str | None = None


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    full_name: str
    role: str
    organization_id: str


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: str
    name: str
    state: str
    subscription_tier: str


class RegisterResponse(BaseModel):
    """Registration response."""

    organization: OrganizationResponse
    user: UserResponse
    tokens: TokenResponse


# === Endpoints ===


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register_organization(
    request: RegisterOrganizationRequest,
    service: AuthServiceDep,
) -> RegisterResponse:
    """
    Register a new organization with admin user.

    Creates the organization and first admin user, returns tokens.
    """
    try:
        org, user = await service.register_organization(
            org_name=request.organization_name,
            admin_email=request.admin_email,
            admin_password=request.admin_password,
            admin_name=request.admin_name,
            license_number=request.license_number,
            state=request.state,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    tokens = service.create_token_pair(user)

    return RegisterResponse(
        organization=OrganizationResponse(
            id=str(org.id),
            name=org.name,
            state=org.state,
            subscription_tier=org.subscription_tier,
        ),
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=str(user.organization_id),
        ),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    """
    Login with email and password.

    Returns access and refresh tokens.
    """
    tokens = await service.login(request.email, request.password)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    tokens = await service.refresh_tokens(request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization_id=str(current_user.organization_id),
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> None:
    """Change the current user's password."""
    success = await service.change_password(
        current_user.id,
        request.current_password,
        request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    request: RegisterUserRequest,
    current_user: CurrentUserDep,
    service: AuthServiceDep,
) -> UserResponse:
    """
    Create a new user in the current organization.

    Requires admin role.
    """
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        user = await service.register_user(
            organization_id=current_user.organization_id,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            phone=request.phone,
            license_number=request.license_number,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=str(user.organization_id),
    )
