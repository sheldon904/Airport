"""Centralized exception handling for Airport API."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


# === Domain Exceptions ===


class AirportException(Exception):
    """Base exception for all Airport domain errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AirportException):
    """Raised when input validation fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class AuthenticationError(AirportException):
    """Raised when authentication fails."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"


class AuthorizationError(AirportException):
    """Raised when user lacks permission."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"


class NotFoundError(AirportException):
    """Raised when a resource is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "Resource not found"

    def __init__(
        self,
        resource_type: str,
        resource_id: str | UUID | None = None,
    ) -> None:
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = str(resource_id)
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message=message, details=details)


class ConflictError(AirportException):
    """Raised when a resource already exists or conflicts."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource conflict"


class DuplicateEmailError(ConflictError):
    """Raised when email is already registered."""

    error_code = "DUPLICATE_EMAIL"
    message = "Email already registered"


class RateLimitError(AirportException):
    """Raised when rate limit is exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."

    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            details={"retry_after": retry_after},
        )


class ServiceUnavailableError(AirportException):
    """Raised when an external service is unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"


class AIServiceError(ServiceUnavailableError):
    """Raised when AI service (Claude) fails."""

    error_code = "AI_SERVICE_ERROR"
    message = "AI service temporarily unavailable"


class StorageError(ServiceUnavailableError):
    """Raised when storage service fails."""

    error_code = "STORAGE_ERROR"
    message = "Storage service temporarily unavailable"


class DocumentProcessingError(AirportException):
    """Raised when document processing fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "DOCUMENT_PROCESSING_ERROR"
    message = "Failed to process document"


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid or expired."""

    error_code = "INVALID_TOKEN"
    message = "Invalid or expired token"


class WeakPasswordError(ValidationError):
    """Raised when password doesn't meet requirements."""

    error_code = "WEAK_PASSWORD"
    message = "Password does not meet security requirements"


class OrganizationNotFoundError(NotFoundError):
    """Raised when organization is not found."""

    def __init__(self, organization_id: UUID | None = None) -> None:
        super().__init__("Organization", organization_id)


class TransactionNotFoundError(NotFoundError):
    """Raised when transaction is not found."""

    def __init__(self, transaction_id: UUID | None = None) -> None:
        super().__init__("Transaction", transaction_id)


class DocumentNotFoundError(NotFoundError):
    """Raised when document is not found."""

    def __init__(self, document_id: UUID | None = None) -> None:
        super().__init__("Document", document_id)


class DeadlineNotFoundError(NotFoundError):
    """Raised when deadline is not found."""

    def __init__(self, deadline_id: UUID | None = None) -> None:
        super().__init__("Deadline", deadline_id)


class UserNotFoundError(NotFoundError):
    """Raised when user is not found."""

    def __init__(self, user_id: UUID | None = None) -> None:
        super().__init__("User", user_id)


# === Exception Handlers ===


async def airport_exception_handler(
    request: Request,
    exc: AirportException,
) -> JSONResponse:
    """Handle all Airport domain exceptions."""
    logger.warning(
        "domain_exception",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        method=request.method,
        details=exc.details,
    )

    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )

    # Add Retry-After header for rate limits
    if isinstance(exc, RateLimitError):
        response.headers["Retry-After"] = str(exc.retry_after)

    # Add WWW-Authenticate header for auth errors
    if isinstance(exc, AuthenticationError):
        response.headers["WWW-Authenticate"] = "Bearer"

    return response


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AirportException, airport_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
