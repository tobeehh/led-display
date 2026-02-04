"""Authentication and session management.

Provides secure session-based authentication with:
- PBKDF2 password hashing
- Secure session tokens
- CSRF protection
"""

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import get_config_manager

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """User session data."""

    token: str
    created_at: float
    expires_at: float
    ip_address: str


class SessionManager:
    """Manages user sessions with secure tokens."""

    def __init__(self, lifetime: int = 86400) -> None:
        """Initialize session manager.

        Args:
            lifetime: Session lifetime in seconds (default: 24 hours)
        """
        self._sessions: dict[str, Session] = {}
        self._lifetime = lifetime

    def create_session(self, ip_address: str) -> str:
        """Create a new session.

        Args:
            ip_address: Client IP address

        Returns:
            Session token
        """
        token = secrets.token_urlsafe(32)
        now = time.time()

        self._sessions[token] = Session(
            token=token,
            created_at=now,
            expires_at=now + self._lifetime,
            ip_address=ip_address,
        )

        self._cleanup_expired()
        logger.debug("Created session for %s", ip_address)

        return token

    def validate_session(self, token: str, ip_address: str | None = None) -> bool:
        """Validate a session token.

        Args:
            token: Session token to validate
            ip_address: Optional IP for additional validation

        Returns:
            True if session is valid
        """
        session = self._sessions.get(token)
        if not session:
            return False

        if time.time() > session.expires_at:
            del self._sessions[token]
            return False

        return True

    def invalidate_session(self, token: str) -> None:
        """Invalidate a session.

        Args:
            token: Session token to invalidate
        """
        self._sessions.pop(token, None)

    def extend_session(self, token: str) -> None:
        """Extend session expiration.

        Args:
            token: Session token to extend
        """
        session = self._sessions.get(token)
        if session:
            session.expires_at = time.time() + self._lifetime

    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        expired = [t for t, s in self._sessions.items() if now > s.expires_at]
        for token in expired:
            del self._sessions[token]


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password using PBKDF2.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations=100000,
    ).hex()

    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against stored hash.

    Args:
        password: Plain text password to verify
        stored_hash: Stored password hash
        salt: Password salt

    Returns:
        True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, stored_hash)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for FastAPI.

    Protects routes requiring authentication and handles
    session validation.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/api/health",
        "/login",
        "/api/auth/login",
        "/api/auth/setup",
        "/static",
        "/favicon.ico",
    }

    # Captive portal detection paths (always public)
    CAPTIVE_PATHS = {
        "/generate_204",
        "/gen_204",
        "/hotspot-detect.html",
        "/library/test/success.html",
        "/connecttest.txt",
        "/ncsi.txt",
    }

    def __init__(self, app, session_manager: SessionManager) -> None:
        super().__init__(app)
        self.session_manager = session_manager

    async def dispatch(self, request: Request, call_next):
        # Allow public paths
        path = request.url.path

        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        if path in self.CAPTIVE_PATHS:
            return await call_next(request)

        # Check if auth is required
        config = get_config_manager().get()
        if not config.web.require_auth:
            return await call_next(request)

        # Check if password is set
        if not config.web.admin_password_hash:
            # No password set - allow access to setup
            return await call_next(request)

        # Validate session
        session_token = request.cookies.get("session")
        client_ip = request.client.host if request.client else "unknown"

        if session_token and self.session_manager.validate_session(session_token, client_ip):
            # Extend session on activity
            self.session_manager.extend_session(session_token)
            return await call_next(request)

        # Not authenticated
        if path.startswith("/api"):
            raise HTTPException(status_code=401, detail="Not authenticated")
        else:
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/login", status_code=303)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    TOKEN_HEADER = "X-CSRF-Token"
    TOKEN_COOKIE = "csrf_token"

    async def dispatch(self, request: Request, call_next):
        # Generate CSRF token if not present
        csrf_token = request.cookies.get(self.TOKEN_COOKIE)
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)

        # Validate token for unsafe methods
        if request.method not in self.SAFE_METHODS:
            cookie_token = request.cookies.get(self.TOKEN_COOKIE)

            if not cookie_token:
                # First request - set token but don't require it
                pass
            else:
                # Check header token
                header_token = request.headers.get(self.TOKEN_HEADER)

                # Also check form data for traditional forms
                form_token = None
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    try:
                        form = await request.form()
                        form_token = form.get("csrf_token")
                    except Exception:
                        pass

                provided_token = header_token or form_token

                if provided_token and not secrets.compare_digest(provided_token, cookie_token):
                    raise HTTPException(status_code=403, detail="CSRF token invalid")

        response = await call_next(request)

        # Set CSRF cookie
        response.set_cookie(
            self.TOKEN_COOKIE,
            csrf_token,
            httponly=True,
            samesite="strict",
            max_age=3600,
        )

        return response


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        block_duration: int = 300,
    ) -> None:
        self.per_minute = requests_per_minute
        self.block_duration = block_duration
        self._requests: dict[str, list[float]] = {}
        self._blocked: dict[str, float] = {}

    def check(self, client_ip: str) -> tuple[bool, str | None]:
        """Check if request is allowed.

        Args:
            client_ip: Client IP address

        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()

        # Check if blocked
        if client_ip in self._blocked:
            if now < self._blocked[client_ip]:
                remaining = int(self._blocked[client_ip] - now)
                return False, f"Rate limited. Try again in {remaining}s"
            else:
                del self._blocked[client_ip]

        # Get request history
        if client_ip not in self._requests:
            self._requests[client_ip] = []

        # Clean old requests
        minute_ago = now - 60
        self._requests[client_ip] = [t for t in self._requests[client_ip] if t > minute_ago]

        # Check rate
        if len(self._requests[client_ip]) >= self.per_minute:
            self._blocked[client_ip] = now + self.block_duration
            return False, "Too many requests"

        # Record request
        self._requests[client_ip].append(now)
        return True, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(self, app, rate_limiter: RateLimiter) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        allowed, error = self.rate_limiter.check(client_ip)
        if not allowed:
            raise HTTPException(status_code=429, detail=error)

        return await call_next(request)
