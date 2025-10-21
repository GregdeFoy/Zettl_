"""
Authentication module for Zettl MCP Server
Handles JWT token validation and user identification
"""

import jwt
import os
from typing import Optional


class MCPAuthenticator:
    """Handles authentication for MCP server requests"""

    def __init__(self, jwt_secret: Optional[str] = None):
        """
        Initialize authenticator with JWT secret

        Args:
            jwt_secret: JWT secret key (from environment if not provided)
        """
        self.jwt_secret = jwt_secret or os.getenv('JWT_SECRET')
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must be provided or set in environment")

    def validate_token(self, token: str) -> Optional[dict]:
        """
        Validate a JWT token and extract claims

        Args:
            token: JWT token string

        Returns:
            Dictionary of claims if valid, None if invalid
        """
        try:
            # Decode and verify the token
            claims = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=['HS256']
            )
            return claims
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_user_id(self, token: str) -> Optional[int]:
        """
        Extract user ID from JWT token

        Args:
            token: JWT token string

        Returns:
            User ID if valid, None if invalid
        """
        claims = self.validate_token(token)
        if claims:
            return claims.get('sub')
        return None
