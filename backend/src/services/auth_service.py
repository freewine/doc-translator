"""Authentication service for JWT token generation and password management."""

import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING

from ..models.user import (
    AuthResult,
    AuthErrorCode,
    User,
    UserStatus,
)

if TYPE_CHECKING:
    from .user_service import UserService, PasswordService
else:
    from .user_service import PasswordService

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles user authentication, password hashing, and JWT token management.
    
    This service provides:
    - Password hashing using bcrypt
    - JWT token generation with configurable expiration
    - JWT token verification and payload extraction
    - DynamoDB-based user authentication (when UserService is provided)
    - Login failure tracking and account locking
    """
    
    # Default JWT expiration: 7 days (168 hours)
    DEFAULT_JWT_EXPIRATION_HOURS = 168
    
    def __init__(
        self,
        jwt_secret: str,
        jwt_expiration_hours: int = 168,
        user_service: Optional["UserService"] = None
    ):
        """
        Initialize the authentication service.

        Args:
            jwt_secret: JWT signing secret key
            jwt_expiration_hours: Token expiration time in hours (default: 168 = 7 days)
            user_service: Optional UserService for DynamoDB-based authentication
        """
        self.jwt_secret = jwt_secret
        self.jwt_expiration_hours = jwt_expiration_hours

        if not self.jwt_secret or len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT secret must be at least 32 characters long. "
                "Set a strong JWT_SECRET in your .env file."
            )

        self.algorithm = "HS256"
        self.user_service = user_service
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt hashed password as a string

        Note:
            Bcrypt has a 72-byte limit. Passwords longer than 72 bytes
            will be truncated before hashing.
        """
        return PasswordService.hash_password(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Bcrypt hash to verify against

        Returns:
            True if password matches hash, False otherwise

        Note:
            Bcrypt has a 72-byte limit. Passwords longer than 72 bytes
            will be truncated before verification to match hashing behavior.
        """
        return PasswordService.verify_password(password, password_hash)

    async def authenticate_user(self, username: str, password: str) -> AuthResult:
        """
        Authenticate a user from DynamoDB and generate a JWT token.
        
        This method:
        - Validates user exists and can login
        - Verifies password
        - Tracks login failures and locks account after 5 attempts
        - Generates JWT with username and role
        - Returns must_change_password flag for new users
        
        Args:
            username: Username provided by user
            password: Password provided by user
            
        Returns:
            AuthResult with success status, token, and user info
        """
        if not self.user_service:
            logger.error("UserService not configured for DynamoDB authentication")
            return AuthResult(
                success=False,
                error="Authentication service not properly configured",
                error_code=AuthErrorCode.TOKEN_INVALID
            )
        
        # Get user from DynamoDB
        user = await self.user_service.get_user(username)
        
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return AuthResult(
                success=False,
                error="Invalid username or password",
                error_code=AuthErrorCode.USER_NOT_FOUND
            )
        
        # Check if user can login (not locked or deleted)
        if user.status == UserStatus.DELETED:
            logger.warning(f"Authentication failed: user '{username}' is deleted")
            return AuthResult(
                success=False,
                error="Account has been deleted",
                error_code=AuthErrorCode.USER_DELETED
            )
        
        if user.status == UserStatus.LOCKED:
            logger.warning(f"Authentication failed: user '{username}' is locked")
            return AuthResult(
                success=False,
                error="Account is locked. Please contact an administrator.",
                error_code=AuthErrorCode.USER_LOCKED,
                remaining_attempts=0
            )
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            
            # Record login failure
            remaining = await self.user_service.record_login_failure(username)
            
            if remaining == 0:
                return AuthResult(
                    success=False,
                    error="Account has been locked due to too many failed attempts",
                    error_code=AuthErrorCode.USER_LOCKED,
                    remaining_attempts=0
                )
            
            return AuthResult(
                success=False,
                error=f"Invalid password. {remaining} attempts remaining.",
                error_code=AuthErrorCode.INVALID_PASSWORD,
                remaining_attempts=remaining
            )
        
        # Reset login failures on successful authentication
        await self.user_service.reset_login_failures(username)
        
        # Generate JWT token with role
        token = self.generate_token(
            username,
            additional_claims={"role": user.role.value}
        )
        
        logger.info(f"User '{username}' authenticated successfully")
        
        return AuthResult(
            success=True,
            token=token,
            user=user,
            must_change_password=user.must_change_password
        )
    
    def generate_token(self, username: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            username: Username to include in token
            additional_claims: Optional additional claims to include in token payload
            
        Returns:
            JWT token string
        """
        # Calculate expiration time
        expiration = datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiration_hours)
        
        # Build token payload
        payload = {
            "sub": username,  # Subject (username)
            "iat": datetime.now(timezone.utc),  # Issued at
            "exp": expiration,  # Expiration time
        }
        
        # Add any additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate and return token
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)
        logger.debug(f"Generated JWT token for user '{username}' expiring at {expiration}")
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT token and extract its payload.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Token payload dictionary if valid, None if invalid or expired
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.algorithm]
            )
            
            logger.debug(f"Token verified for user '{payload.get('sub')}'")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    def get_username_from_token(self, token: str) -> Optional[str]:
        """
        Extract username from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Username if token is valid, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
    
    def get_role_from_token(self, token: str) -> Optional[str]:
        """
        Extract role from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Role if token is valid and contains role, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("role")
        return None


def create_password_hash(password: str) -> str:
    """
    Utility function to create a password hash for initial setup.

    This is a convenience function for generating password hashes
    to be stored in the configuration file.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password

    Note:
        Bcrypt has a 72-byte limit. Passwords longer than 72 bytes
        will be truncated before hashing.

    Example:
        >>> hash = create_password_hash("my_secure_password")
        >>> print(hash)
        $2b$12$...
    """
    return PasswordService.hash_password(password)


if __name__ == "__main__":
    # Example usage for generating password hashes
    import sys
    
    if len(sys.argv) > 1:
        password = sys.argv[1]
        hash_value = create_password_hash(password)
        print(f"Password hash: {hash_value}")
    else:
        print("Usage: python auth_service.py <password>")
        print("Example: python auth_service.py my_secure_password")
