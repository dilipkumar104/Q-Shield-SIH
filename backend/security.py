"""Security validation helpers and middleware."""
import html
import re
from typing import Any, Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from config import settings

logger = logging.getLogger(__name__)

# Supported quantum states
VALID_STATES = {"|0>", "|1>", "|+>", "|->"}

# Supported attack types
VALID_ATTACK_TYPES = {"forgery", "impersonation", "replay", "channel"}

# Supported measurement bases
VALID_BASIS = {"Z", "X"}

# Supported export formats
VALID_EXPORT_FORMATS = {"json", "csv", "markdown"}

# Detection methods
VALID_DETECTION_METHODS = {"tv_distance", "chi_square", "both"}


class SecurityValidator:
    """Input validation and sanitization for API requests."""

    @staticmethod
    def validate_state(state: str) -> str:
        """Validate quantum state parameter.

        Args:
            state: Quantum state string

        Returns:
            Validated state

        Raises:
            ValueError: If state is invalid
        """
        if state not in VALID_STATES:
            raise ValueError(f"State must be one of {VALID_STATES}")
        return state

    @staticmethod
    def validate_shots(shots: int) -> int:
        """Validate shots parameter.

        Args:
            shots: Number of measurement shots

        Returns:
            Validated shots value

        Raises:
            ValueError: If shots is out of range
        """
        if not (100 <= shots <= 100000):
            raise ValueError("Shots must be between 100 and 100,000")
        return shots

    @staticmethod
    def validate_seed(seed: Optional[int]) -> Optional[int]:
        """Validate random seed parameter.

        Args:
            seed: Random seed value

        Returns:
            Validated seed

        Raises:
            ValueError: If seed is out of range
        """
        if seed is not None:
            max_seed = 2**31 - 1  # 2147483647
            if not (0 <= seed <= max_seed):
                raise ValueError(f"Seed must be between 0 and {max_seed}")
        return seed

    @staticmethod
    def validate_threshold(threshold: float) -> float:
        """Validate detection threshold.

        Args:
            threshold: Threshold value

        Returns:
            Validated threshold

        Raises:
            ValueError: If threshold is out of range
        """
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return threshold

    @staticmethod
    def validate_attack_intensity(intensity: float) -> float:
        """Validate attack intensity.

        Args:
            intensity: Attack intensity value

        Returns:
            Validated intensity

        Raises:
            ValueError: If intensity is out of range
        """
        if not (0.0 <= intensity <= 1.0):
            raise ValueError("Attack intensity must be between 0.0 and 1.0")
        return intensity

    @staticmethod
    def validate_attack_type(attack_type: str) -> str:
        """Validate attack type.

        Args:
            attack_type: Attack type string

        Returns:
            Validated attack type

        Raises:
            ValueError: If attack type is invalid
        """
        if attack_type not in VALID_ATTACK_TYPES:
            raise ValueError(f"Attack type must be one of {VALID_ATTACK_TYPES}")
        return attack_type

    @staticmethod
    def validate_measurement_basis(basis: str) -> str:
        """Validate measurement basis.

        Args:
            basis: Measurement basis

        Returns:
            Validated basis

        Raises:
            ValueError: If basis is invalid
        """
        if basis not in VALID_BASIS:
            raise ValueError(f"Measurement basis must be one of {VALID_BASIS}")
        return basis

    @staticmethod
    def validate_export_format(format_str: str) -> str:
        """Validate export format.

        Args:
            format_str: Export format

        Returns:
            Validated format

        Raises:
            ValueError: If format is invalid
        """
        if format_str not in VALID_EXPORT_FORMATS:
            raise ValueError(f"Export format must be one of {VALID_EXPORT_FORMATS}")
        return format_str

    @staticmethod
    def validate_detection_method(method: str) -> str:
        """Validate detection method.

        Args:
            method: Detection method

        Returns:
            Validated method

        Raises:
            ValueError: If method is invalid
        """
        if method not in VALID_DETECTION_METHODS:
            raise ValueError(f"Detection method must be one of {VALID_DETECTION_METHODS}")
        return method


class ExportSanitizer:
    """Sanitize user data for export formats."""

    @staticmethod
    def sanitize_for_csv(value: Any) -> str:
        """Sanitize value for CSV export to prevent CSV injection.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized string safe for CSV
        """
        if value is None:
            return ""
        str_val = str(value)
        # Check for formulas: =, +, -, @, tab, CR, LF
        if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
            # Prefix with single quote to prevent formula execution
            return f"'{str_val}"
        return str_val

    @staticmethod
    def sanitize_for_markdown(value: Any) -> str:
        """Sanitize value for Markdown export to prevent XSS.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized string safe for Markdown
        """
        if value is None:
            return ""
        # HTML escape to prevent XSS in rendered Markdown
        return html.escape(str(value))

    @staticmethod
    def sanitize_for_json(value: Any) -> Any:
        """Sanitize value for JSON export.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value for JSON
        """
        if isinstance(value, str):
            # Remove control characters that could cause issues
            return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        elif isinstance(value, dict):
            return {k: ExportSanitizer.sanitize_for_json(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [ExportSanitizer.sanitize_for_json(v) for v in value]
        return value


class SecurityHeadersMiddleware:
    """Middleware to add security headers to responses."""

    @staticmethod
    async def __call__(request: Request, call_next):
        """Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key from request.

    Args:
        request: FastAPI request

    Returns:
        IP address for rate limiting
    """
    # Use X-Forwarded-For if behind proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors.

    Args:
        request: FastAPI request
        exc: Rate limit exception

    Returns:
        JSON error response
    """
    logger.warning(
        f"Rate limit exceeded for IP: {get_rate_limit_key(request)}",
        extra={"ip": get_rate_limit_key(request), "limit": exc.detail}
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(exc, "retry_after", 60)
        }
    )


def validate_run_id(run_id: str) -> str:
    """Validate run ID format to prevent path traversal.

    Args:
        run_id: Run ID string

    Returns:
        Validated run ID

    Raises:
        HTTPException: If run ID is invalid
    """
    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run ID format"
        )
    return run_id


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error message for user-facing responses.

    Args:
        error: Original exception

    Returns:
        User-friendly error message
    """
    # Map common exceptions to user-friendly messages
    error_type = type(error).__name__

    friendly_messages = {
        "ValueError": "Invalid parameter value",
        "KeyError": "Required field missing",
        "TypeError": "Invalid data type",
        "AttributeError": "Invalid attribute",
    }

    if error_type in friendly_messages:
        return friendly_messages[error_type]

    # Generic message for unexpected errors
    return "An internal error occurred"