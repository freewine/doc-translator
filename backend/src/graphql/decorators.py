"""
GraphQL authentication and authorization decorators.

This module provides decorators for protecting GraphQL resolvers:
- @require_auth: Requires valid JWT token
- @require_admin: Requires admin role
- @require_role: Requires specific role(s)
"""
import functools
import logging
from typing import Any, Callable, List, Optional, TypeVar, Union

from strawberry.types import Info

from ..models.user import User, UserRole, AuthErrorCode

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, error_code: AuthErrorCode = AuthErrorCode.TOKEN_INVALID):
        super().__init__(message)
        self.error_code = error_code


class PermissionError(Exception):
    """Raised when authorization fails."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = AuthErrorCode.PERMISSION_DENIED


def get_token_from_context(info: Info) -> Optional[str]:
    """
    Extract JWT token from GraphQL context.

    Looks for token in:
    1. info.context.get("token")
    2. info.context["request"].headers["Authorization"] (Bearer token)

    Args:
        info: Strawberry Info object

    Returns:
        JWT token string if found, None otherwise
    """
    context = info.context

    # Check if token is directly in context
    if hasattr(context, "get") and context.get("token"):
        return context.get("token")

    # Get request object - handle both dict and object contexts
    request = None
    if isinstance(context, dict):
        request = context.get("request")
    elif hasattr(context, "request"):
        request = context.request

    # Check Authorization header
    if request and hasattr(request, "headers"):
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

    return None


def get_current_user_from_context(info: Info) -> Optional[User]:
    """
    Get the current authenticated user from GraphQL context.

    Args:
        info: Strawberry Info object

    Returns:
        User object if authenticated, None otherwise
    """
    context = info.context

    # Handle both dict and object contexts
    if isinstance(context, dict):
        return context.get("current_user")

    if hasattr(context, "get"):
        return context.get("current_user")

    if hasattr(context, "current_user"):
        return context.current_user

    return None


def get_auth_service_from_context(info: Info):
    """
    Get AuthService from GraphQL context.

    Args:
        info: Strawberry Info object

    Returns:
        AuthService instance
    """
    context = info.context

    # Handle both dict and object contexts
    if isinstance(context, dict):
        return context.get("auth_service")

    if hasattr(context, "get"):
        return context.get("auth_service")

    if hasattr(context, "auth_service"):
        return context.auth_service

    return None


async def verify_and_get_user(info: Info) -> User:
    """
    Verify JWT token and get user from context or token.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        User object
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    # First check if user is already in context
    user = get_current_user_from_context(info)
    if user:
        return user
    
    # Get token from context
    token = get_token_from_context(info)
    if not token:
        raise AuthenticationError(
            "Authentication required",
            AuthErrorCode.TOKEN_INVALID
        )
    
    # Get auth service
    auth_service = get_auth_service_from_context(info)
    if not auth_service:
        raise AuthenticationError(
            "Authentication service not available",
            AuthErrorCode.TOKEN_INVALID
        )
    
    # Verify token
    payload = auth_service.verify_token(token)
    if not payload:
        raise AuthenticationError(
            "Invalid or expired token",
            AuthErrorCode.TOKEN_EXPIRED
        )
    
    # Get user from user service if available
    username = payload.get("sub")
    if not username:
        raise AuthenticationError(
            "Invalid token payload",
            AuthErrorCode.TOKEN_INVALID
        )
    
    # Try to get full user from user service
    context = info.context
    user_service = None
    if isinstance(context, dict):
        user_service = context.get("user_service")
    elif hasattr(context, "get"):
        user_service = context.get("user_service")
    if user_service:
        user = await user_service.get_user(username)
        if not user:
            raise AuthenticationError(
                "User not found",
                AuthErrorCode.USER_NOT_FOUND
            )
        return user
    
    # Fallback: create minimal user from token payload
    role_str = payload.get("role", "user")
    return User(
        username=username,
        password_hash="",  # Not needed for authorization
        role=UserRole(role_str),
    )


def require_auth(func: F) -> F:
    """
    Decorator that requires a valid JWT token.
    
    Usage:
        @strawberry.field
        @require_auth
        async def protected_query(self, info: Info) -> str:
            user = get_current_user_from_context(info)
            return f"Hello, {user.username}"
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Find info argument
        info = None
        for arg in args:
            if isinstance(arg, Info):
                info = arg
                break
        if info is None:
            info = kwargs.get("info")
        
        if info is None:
            raise AuthenticationError("GraphQL Info not found")
        
        # Verify authentication
        user = await verify_and_get_user(info)
        
        # Store user in context for later use
        if hasattr(info.context, "__setitem__"):
            info.context["current_user"] = user
        elif hasattr(info.context, "current_user"):
            info.context.current_user = user
        
        return await func(*args, **kwargs)
    
    return wrapper  # type: ignore


def require_admin(func: F) -> F:
    """
    Decorator that requires admin role.
    
    Usage:
        @strawberry.field
        @require_admin
        async def admin_only_query(self, info: Info) -> str:
            return "Admin access granted"
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Find info argument
        info = None
        for arg in args:
            if isinstance(arg, Info):
                info = arg
                break
        if info is None:
            info = kwargs.get("info")
        
        if info is None:
            raise AuthenticationError("GraphQL Info not found")
        
        # Verify authentication
        user = await verify_and_get_user(info)
        
        # Check admin role
        if user.role != UserRole.ADMIN:
            raise PermissionError("Admin access required")
        
        # Store user in context
        if hasattr(info.context, "__setitem__"):
            info.context["current_user"] = user
        elif hasattr(info.context, "current_user"):
            info.context.current_user = user
        
        return await func(*args, **kwargs)
    
    return wrapper  # type: ignore


def require_role(*roles: str) -> Callable[[F], F]:
    """
    Decorator that requires one of the specified roles.
    
    Usage:
        @strawberry.field
        @require_role("admin", "moderator")
        async def moderator_query(self, info: Info) -> str:
            return "Access granted"
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find info argument
            info = None
            for arg in args:
                if isinstance(arg, Info):
                    info = arg
                    break
            if info is None:
                info = kwargs.get("info")
            
            if info is None:
                raise AuthenticationError("GraphQL Info not found")
            
            # Verify authentication
            user = await verify_and_get_user(info)
            
            # Check role
            if user.role.value not in roles:
                raise PermissionError(f"Required role: {', '.join(roles)}")
            
            # Store user in context
            if hasattr(info.context, "__setitem__"):
                info.context["current_user"] = user
            elif hasattr(info.context, "current_user"):
                info.context.current_user = user
            
            return await func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator
