"""
JWT token validation middleware.

Middleware for validating JWT tokens on protected routes.
"""

from fastapi import Request, HTTPException, status
from src.security import decode_token
import structlog
from typing import Optional

logger = structlog.get_logger()


class JWTValidationMiddleware:
    """
    Middleware for JWT token validation.

    Validates Bearer token on authorization header.
    """

    def __init__(self, app, protected_paths: Optional[list] = None):
        self.app = app
        self.protected_paths = protected_paths or []

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        
        # Check if path requires protection
        requires_protection = any(
            path.startswith(protected_path) for protected_path in self.protected_paths
        )

        if requires_protection:
            # Extract and validate authorization header
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()

            if not auth_header.startswith("Bearer "):
                logger.warning("missing_bearer_token", path=path)
                
                # Return 401 Unauthorized
                await send({
                    "type": "http.response.start",
                    "status": status.HTTP_401_UNAUTHORIZED,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "Missing or invalid authorization token"}',
                })
                return

            # Extract token
            token = auth_header[7:]

            # Validate token
            payload = decode_token(token)
            if not payload:
                logger.warning("invalid_token", path=path)
                
                # Return 401 Unauthorized
                await send({
                    "type": "http.response.start",
                    "status": status.HTTP_401_UNAUTHORIZED,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "Invalid or expired token"}',
                })
                return

            # Add user info to scope for downstream handlers
            scope["user_id"] = payload.get("sub")

        await self.app(scope, receive, send)
