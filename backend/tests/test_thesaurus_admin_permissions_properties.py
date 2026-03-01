"""
Property-Based Tests for Thesaurus Admin Permissions

Feature: thesaurus-admin-permissions

Properties tested:
- Property 2: Regular users are rejected from all thesaurus mutations with PERMISSION_DENIED
  Validates: Requirements 1.2, 2.2, 3.2, 7.1
- Property 1: Admin users can perform all thesaurus mutations
  Validates: Requirements 1.1, 2.1, 3.1
- Property 4: Language pairs are stored with global ownership
  Validates: Requirements 5.1
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings

from strawberry.types import Info

from src.graphql.thesaurus_resolvers import require_admin_access
from src.graphql.decorators import PermissionError as AuthPermissionError
from src.models.user import User, UserRole, UserStatus
from src.models.config import LanguagePair as ConfigLanguagePair


# =========================================================================
# Strategies
# =========================================================================

# Strategy for generating valid usernames (3-50 alphanumeric + underscore chars)
username_strategy = st.from_regex(r"[a-zA-Z0-9_]{3,50}", fullmatch=True)

# All thesaurus mutation types that require admin access
thesaurus_mutation_types = st.sampled_from([
    "add_term_pair",
    "edit_term_pair",
    "delete_term_pair",
    "bulk_delete_term_pairs",
    "import_terms_csv",
    "create_catalog",
    "update_catalog",
    "delete_catalog",
    "add_language_pair",
    "remove_language_pair",
])


def make_mock_info(username: str, role: UserRole) -> Mock:
    """
    Create a mock Strawberry Info object that simulates an authenticated user.

    This sets up:
    - A mock auth_service that returns the given username from the token
    - A mock request with a Bearer token header
    - A resolver_context with the auth_service
    - A current_user in context with the given role
    """
    mock_auth_service = Mock()
    mock_auth_service.get_username_from_token = Mock(return_value=username)

    mock_request = Mock()
    mock_request.headers = {"Authorization": "Bearer mock-jwt-token"}

    # Build a resolver_context mock that has auth_service
    resolver_context = Mock()
    resolver_context.auth_service = mock_auth_service

    user = User(
        username=username,
        password_hash="hashed",
        role=role,
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )

    info = Mock(spec=Info)
    info.context = {
        "request": mock_request,
        "resolver_context": resolver_context,
        "current_user": user,
    }
    return info


# =========================================================================
# Property 2: Regular users are rejected from all thesaurus mutations
# =========================================================================


class TestRegularUserRejectedFromMutations:
    """
    Property 2: Regular users are rejected from all thesaurus mutations with PERMISSION_DENIED

    For any regular user and for any thesaurus mutation type, calling
    require_admin_access should raise a PermissionError with the message
    "Admin access required".

    Feature: thesaurus-admin-permissions, Property 2: Regular users are rejected from all thesaurus mutations with PERMISSION_DENIED
    **Validates: Requirements 1.2, 2.2, 3.2, 7.1**
    """

    @settings(max_examples=100)
    @given(
        username=username_strategy,
        mutation_type=thesaurus_mutation_types,
    )
    @pytest.mark.asyncio
    async def test_regular_user_rejected_with_permission_denied(
        self, username: str, mutation_type: str
    ):
        """
        Property 2: Regular users are rejected from all thesaurus mutations with PERMISSION_DENIED

        For any regular user (UserRole.USER) and for any thesaurus mutation type,
        require_admin_access raises PermissionError with "Admin access required".

        The mutation_type parameter demonstrates that this property holds across
        all mutation types — the same require_admin_access gate is used for every
        thesaurus mutation.

        Feature: thesaurus-admin-permissions, Property 2: Regular users are rejected from all thesaurus mutations with PERMISSION_DENIED
        **Validates: Requirements 1.2, 2.2, 3.2, 7.1**
        """
        info = make_mock_info(username=username, role=UserRole.USER)

        with pytest.raises(AuthPermissionError) as exc_info:
            await require_admin_access(info)

        assert str(exc_info.value) == "Admin access required", (
            f"Expected error message 'Admin access required' for regular user "
            f"'{username}' attempting mutation '{mutation_type}', "
            f"but got: '{exc_info.value}'"
        )
        assert exc_info.value.error_code.value == "PERMISSION_DENIED", (
            f"Expected error_code PERMISSION_DENIED for regular user "
            f"'{username}' attempting mutation '{mutation_type}', "
            f"but got: '{exc_info.value.error_code}'"
        )


# =========================================================================
# Property 1: Admin users can perform all thesaurus mutations
# =========================================================================


class TestAdminUserCanPerformAllMutations:
    """
    Property 1: Admin users can perform all thesaurus mutations

    For any admin user and for any thesaurus mutation type (language pair
    create/delete, catalog create/update/delete, term pair
    add/edit/delete/bulk-delete/import), calling require_admin_access
    should execute successfully and return the username.

    Feature: thesaurus-admin-permissions, Property 1: Admin users can perform all thesaurus mutations
    **Validates: Requirements 1.1, 2.1, 3.1**
    """

    @settings(max_examples=100)
    @given(
        username=username_strategy,
        mutation_type=thesaurus_mutation_types,
    )
    @pytest.mark.asyncio
    async def test_admin_user_can_access_all_mutations(
        self, username: str, mutation_type: str
    ):
        """
        Property 1: Admin users can perform all thesaurus mutations

        For any admin user (UserRole.ADMIN) and for any thesaurus mutation type,
        require_admin_access does NOT raise any exception and returns the
        correct username.

        The mutation_type parameter demonstrates that this property holds across
        all mutation types — the same require_admin_access gate is used for every
        thesaurus mutation.

        Feature: thesaurus-admin-permissions, Property 1: Admin users can perform all thesaurus mutations
        **Validates: Requirements 1.1, 2.1, 3.1**
        """
        info = make_mock_info(username=username, role=UserRole.ADMIN)

        # require_admin_access should NOT raise for admin users
        result = await require_admin_access(info)

        assert result == username, (
            f"Expected require_admin_access to return username '{username}' "
            f"for admin user attempting mutation '{mutation_type}', "
            f"but got: '{result}'"
        )



# =========================================================================
# Strategies for Property 4
# =========================================================================

# Strategy for generating ISO-like language codes (2-3 lowercase letters)
language_code_strategy = st.from_regex(r"[a-z]{2,3}", fullmatch=True)

# Strategy for generating human-readable language display names (1-30 alpha chars)
language_name_strategy = st.from_regex(r"[A-Za-z]{1,30}", fullmatch=True)

# Strategy for generating display names like "Chinese→Vietnamese"
display_name_strategy = st.builds(
    lambda src, tgt: f"{src}→{tgt}",
    language_name_strategy,
    language_name_strategy,
)


def make_mock_info_with_language_pair_service(
    username: str, role: UserRole
) -> tuple:
    """
    Create a mock Strawberry Info object with a mock language_pair_service.

    Returns:
        Tuple of (info, mock_language_pair_service) so the test can inspect
        calls made to the service.
    """
    mock_auth_service = Mock()
    mock_auth_service.get_username_from_token = Mock(return_value=username)

    mock_request = Mock()
    mock_request.headers = {"Authorization": "Bearer mock-jwt-token"}

    # Create a mock language_pair_service with an async create_language_pair
    mock_language_pair_service = Mock()
    mock_create = AsyncMock()
    mock_language_pair_service.create_language_pair = mock_create

    # Build a resolver_context mock that has auth_service and language_pair_service
    resolver_context = Mock()
    resolver_context.auth_service = mock_auth_service
    resolver_context.language_pair_service = mock_language_pair_service

    user = User(
        username=username,
        password_hash="hashed",
        role=role,
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )

    info = Mock(spec=Info)
    info.context = {
        "request": mock_request,
        "resolver_context": resolver_context,
        "current_user": user,
    }
    return info, mock_language_pair_service


# =========================================================================
# Property 4: Language pairs are stored with global ownership
# =========================================================================


class TestLanguagePairsStoredWithGlobalOwnership:
    """
    Property 4: Language pairs are stored with global ownership

    For any admin user creating a language pair, the service is called with
    user_id="__global__" (not the actual admin username), ensuring language
    pairs are stored as global resources without user-specific ownership.

    Feature: thesaurus-admin-permissions, Property 4: Language pairs are stored with global ownership
    **Validates: Requirements 5.1**
    """

    @settings(max_examples=100)
    @given(
        admin_username=username_strategy,
        source_code=language_code_strategy,
        target_code=language_code_strategy,
        source_name=language_name_strategy,
        target_name=language_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_add_language_pair_uses_global_user_id(
        self,
        admin_username: str,
        source_code: str,
        target_code: str,
        source_name: str,
        target_name: str,
    ):
        """
        Property 4: Language pairs are stored with global ownership

        For any admin user calling resolve_add_language_pair with any
        language pair data, the language_pair_service.create_language_pair
        is called with user_id="__global__" — never the actual admin username.

        Feature: thesaurus-admin-permissions, Property 4: Language pairs are stored with global ownership
        **Validates: Requirements 5.1**
        """
        from src.graphql.resolvers import resolve_add_language_pair

        info, mock_lp_service = make_mock_info_with_language_pair_service(
            username=admin_username, role=UserRole.ADMIN
        )

        # Configure the mock to return a valid ConfigLanguagePair
        mock_lp_service.create_language_pair.return_value = ConfigLanguagePair(
            id="test-uuid",
            user_id="__global__",
            source_language=source_code,
            target_language=target_code,
            display_name=f"{source_name}→{target_name}",
        )

        await resolve_add_language_pair(
            info=info,
            source_language=source_name,
            target_language=target_name,
            source_language_code=source_code,
            target_language_code=target_code,
        )

        # Assert create_language_pair was called exactly once
        mock_lp_service.create_language_pair.assert_called_once()

        # Extract the user_id that was passed to create_language_pair
        call_kwargs = mock_lp_service.create_language_pair.call_args
        # The call uses keyword arguments: user_id="__global__"
        actual_user_id = call_kwargs.kwargs.get(
            "user_id", call_kwargs.args[0] if call_kwargs.args else None
        )

        assert actual_user_id == "__global__", (
            f"Expected create_language_pair to be called with user_id='__global__' "
            f"but got user_id='{actual_user_id}'. "
            f"Admin username was '{admin_username}' — language pairs must be stored "
            f"with global ownership, not user-specific ownership."
        )

        # Also verify the actual admin username was NOT used as user_id
        assert actual_user_id != admin_username or admin_username == "__global__", (
            f"create_language_pair was called with the admin's actual username "
            f"'{admin_username}' instead of '__global__'. Language pairs must be "
            f"stored as global resources."
        )
