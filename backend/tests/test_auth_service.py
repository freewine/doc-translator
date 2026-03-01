"""Tests for AuthService including property-based tests."""

import jwt
import time
from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st, settings, assume
import pytest

from src.services.auth_service import AuthService, create_password_hash


# Strategies for generating test data
@st.composite
def username_strategy(draw):
    """Generate valid usernames."""
    return draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-.'
        )
    ))


@st.composite
def password_strategy(draw):
    """Generate valid passwords."""
    return draw(st.text(
        min_size=8,
        max_size=100,
        alphabet=st.characters(
            min_codepoint=33,
            max_codepoint=126
        )
    ))


@st.composite
def jwt_secret_strategy(draw):
    """Generate valid JWT secrets."""
    return draw(st.text(
        min_size=32,
        max_size=128,
        alphabet=st.characters(
            min_codepoint=33,
            max_codepoint=126
        )
    ))


class TestAuthServiceBasic:
    """Basic unit tests for AuthService."""
    
    def test_password_hashing_produces_valid_bcrypt_hash(self):
        """Test that password hashing produces a valid bcrypt hash."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        password = "test_password_123"
        
        hashed = auth_service.hash_password(password)
        
        # Bcrypt hashes start with $2b$ and are 60 characters long
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
    
    def test_password_verification_succeeds_with_correct_password(self):
        """Test that password verification succeeds with correct password."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        password = "test_password_123"
        
        hashed = auth_service.hash_password(password)
        result = auth_service.verify_password(password, hashed)
        
        assert result is True
    
    def test_password_verification_fails_with_incorrect_password(self):
        """Test that password verification fails with incorrect password."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        
        hashed = auth_service.hash_password(password)
        result = auth_service.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_token_generation_creates_valid_jwt(self):
        """Test that token generation creates a valid JWT."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        username = "admin"
        
        token = auth_service.generate_token(username)
        
        # Verify it's a valid JWT structure (3 parts separated by dots)
        parts = token.split('.')
        assert len(parts) == 3
    
    def test_token_verification_succeeds_with_valid_token(self):
        """Test that token verification succeeds with valid token."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        username = "admin"
        
        token = auth_service.generate_token(username)
        payload = auth_service.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == username
        assert "iat" in payload
        assert "exp" in payload
    
    def test_token_verification_fails_with_invalid_token(self):
        """Test that token verification fails with invalid token."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        
        invalid_token = "invalid.token.here"
        payload = auth_service.verify_token(invalid_token)
        
        assert payload is None
    
    def test_token_verification_fails_with_wrong_secret(self):
        """Test that token verification fails when using wrong secret."""
        auth_service1 = AuthService("secret_key_1_12345678901234567890")
        auth_service2 = AuthService("secret_key_2_12345678901234567890")
        
        token = auth_service1.generate_token("admin")
        payload = auth_service2.verify_token(token)
        
        assert payload is None
    
    def test_expired_token_verification_fails(self):
        """Test that expired token verification fails."""
        # Create service with very short expiration
        auth_service = AuthService(
            "test_secret_key_12345678901234567890",
            jwt_expiration_hours=0  # Will create expired token
        )
        
        # Manually create an expired token
        expiration = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "admin",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": expiration
        }
        expired_token = jwt.encode(payload, auth_service.jwt_secret, algorithm=auth_service.algorithm)
        
        result = auth_service.verify_token(expired_token)
        
        assert result is None
    
    def test_get_username_from_valid_token(self):
        """Test extracting username from valid token."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        username = "testuser"
        
        token = auth_service.generate_token(username)
        extracted_username = auth_service.get_username_from_token(token)
        
        assert extracted_username == username
    
    def test_get_username_from_invalid_token_returns_none(self):
        """Test that extracting username from invalid token returns None."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        
        extracted_username = auth_service.get_username_from_token("invalid.token")
        
        assert extracted_username is None
    
    def test_token_contains_additional_claims(self):
        """Test that additional claims are included in token."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        username = "admin"
        additional_claims = {"role": "administrator", "permissions": ["read", "write"]}
        
        token = auth_service.generate_token(username, additional_claims)
        payload = auth_service.verify_token(token)
        
        assert payload is not None
        assert payload["role"] == "administrator"
        assert payload["permissions"] == ["read", "write"]
    
    def test_create_password_hash_utility_function(self):
        """Test the utility function for creating password hashes."""
        password = "test_password"
        
        hash_value = create_password_hash(password)
        
        assert hash_value.startswith("$2b$")
        assert len(hash_value) == 60
        
        # Verify the hash works
        auth_service = AuthService("test_secret_key_12345678901234567890")
        assert auth_service.verify_password(password, hash_value) is True


class TestAuthServiceProperties:
    """Property-based tests for AuthService."""
    
    @given(
        password=password_strategy(),
        jwt_secret=jwt_secret_strategy()
    )
    @settings(max_examples=50, deadline=2000)  # Bcrypt is slow by design
    def test_property_4_password_hashing_compliance(self, password, jwt_secret):
        """
        Feature: excel-translation-refactor, Property 4: Password hashing compliance
        
        For any password stored in the configuration file, the password should be
        hashed using bcrypt algorithm with valid salt rounds.
        
        Validates: Requirements 1.5
        """
        auth_service = AuthService(jwt_secret)
        
        # Hash the password
        hashed = auth_service.hash_password(password)
        
        # Verify it's a valid bcrypt hash
        # Bcrypt hashes have the format: $2b$rounds$salt+hash
        assert hashed.startswith("$2b$12$"), "Hash should use bcrypt with 12 rounds"
        assert len(hashed) == 60, "Bcrypt hash should be 60 characters"
        
        # Verify the hash can be used to verify the original password
        assert auth_service.verify_password(password, hashed) is True
    
    @given(
        username=username_strategy(),
        jwt_secret=jwt_secret_strategy()
    )
    @settings(max_examples=50, deadline=2000)
    def test_property_2_valid_token_generation(self, username, jwt_secret):
        """
        Feature: excel-translation-refactor, Property 2: Valid token generation

        For any valid username, when a token is generated, it should be verifiable.

        Validates: Requirements 1.3
        """
        auth_service = AuthService(jwt_secret, jwt_expiration_hours=24)

        # Generate token directly
        token = auth_service.generate_token(username)

        # Token should be generated
        assert token is not None, "Token should be generated"
        assert isinstance(token, str), "Token should be a string"

        # Token should be verifiable
        payload = auth_service.verify_token(token)
        assert payload is not None, "Generated token should be verifiable"
        assert payload["sub"] == username, "Token should contain the username"

        # Token should have required claims
        assert "iat" in payload, "Token should have issued-at claim"
        assert "exp" in payload, "Token should have expiration claim"

        # Expiration should be in the future
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > now_timestamp, "Token expiration should be in the future"

    @given(
        correct_password=password_strategy(),
        wrong_password=password_strategy(),
        jwt_secret=jwt_secret_strategy()
    )
    @settings(max_examples=50, deadline=2000)  # Bcrypt is slow by design
    def test_property_3_password_verification_rejection(self, correct_password,
                                                        wrong_password, jwt_secret):
        """
        Feature: excel-translation-refactor, Property 3: Password verification rejection

        For any incorrect password, verification should fail.

        Validates: Requirements 1.4
        """
        # Ensure passwords are different
        assume(correct_password != wrong_password)

        auth_service = AuthService(jwt_secret)

        # Hash the correct password
        password_hash = auth_service.hash_password(correct_password)

        # Wrong password should fail verification
        result = auth_service.verify_password(wrong_password, password_hash)
        assert result is False, "Wrong password should fail verification"

        # Correct password should pass verification
        result = auth_service.verify_password(correct_password, password_hash)
        assert result is True, "Correct password should pass verification"

    @given(
        username=username_strategy(),
        jwt_secret=jwt_secret_strategy(),
        expiration_hours=st.integers(min_value=1, max_value=168)
    )
    @settings(max_examples=100)
    def test_token_expiration_configuration(self, username, jwt_secret, expiration_hours):
        """
        Test that token expiration is configurable and correctly applied.
        """
        auth_service = AuthService(
            jwt_secret,
            jwt_expiration_hours=expiration_hours
        )
        
        # Generate token
        token = auth_service.generate_token(username)
        payload = auth_service.verify_token(token)
        
        assert payload is not None
        
        # Calculate expected expiration range
        now = datetime.now(timezone.utc)
        expected_exp = now + timedelta(hours=expiration_hours)
        
        # Get actual expiration from token
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        # Allow 5 second tolerance for test execution time
        time_diff = abs((actual_exp - expected_exp).total_seconds())
        assert time_diff < 5, f"Token expiration should be {expiration_hours} hours from now"
    
    @given(
        password=password_strategy(),
        jwt_secret=jwt_secret_strategy()
    )
    @settings(max_examples=50, deadline=3000)  # Bcrypt is slow, hashing twice takes longer
    def test_password_hash_uniqueness(self, password, jwt_secret):
        """
        Test that hashing the same password twice produces different hashes
        (due to different salts).
        """
        auth_service = AuthService(jwt_secret)
        
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Hashes should be different (different salts)
        assert hash1 != hash2, "Same password should produce different hashes"
        
        # But both should verify the original password
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True
    
    @given(
        username=username_strategy(),
        password=password_strategy(),
        jwt_secret=jwt_secret_strategy()
    )
    @settings(max_examples=20, deadline=3000)  # Bcrypt is slow, full flow takes longer
    def test_round_trip_password_and_token_flow(self, username, password, jwt_secret):
        """
        Test complete flow: hash password -> verify password -> generate token -> verify token.
        """
        auth_service = AuthService(jwt_secret)

        # Step 1: Hash password (as would be done during setup)
        password_hash = auth_service.hash_password(password)

        # Step 2: Verify password
        assert auth_service.verify_password(password, password_hash) is True

        # Step 3: Generate token
        token = auth_service.generate_token(username)
        assert token is not None

        # Step 4: Verify token
        payload = auth_service.verify_token(token)
        assert payload is not None

        # Step 5: Extract username from token
        extracted_username = auth_service.get_username_from_token(token)
        assert extracted_username == username
    
    def test_empty_password_handling(self):
        """Test that empty passwords are handled correctly."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        
        # Empty password should still be hashable
        empty_password = ""
        hashed = auth_service.hash_password(empty_password)
        
        assert hashed.startswith("$2b$")
        assert auth_service.verify_password(empty_password, hashed) is True
    
    def test_unicode_password_handling(self):
        """Test that Unicode passwords are handled correctly."""
        auth_service = AuthService("test_secret_key_12345678901234567890")
        
        # Unicode password
        unicode_password = "密码🔐パスワード"
        hashed = auth_service.hash_password(unicode_password)
        
        assert hashed.startswith("$2b$")
        assert auth_service.verify_password(unicode_password, hashed) is True
    
    def test_very_long_password_handling(self):
        """Test that very long passwords are handled correctly."""
        auth_service = AuthService("test_secret_key_12345678901234567890")

        # Very long password (bcrypt has a 72 byte limit)
        long_password = "a" * 200
        hashed = auth_service.hash_password(long_password)

        assert hashed.startswith("$2b$")
        # Note: bcrypt truncates at 72 bytes, so this should still work
        assert auth_service.verify_password(long_password, hashed) is True


class TestJWTSecretEnforcement:
    """Tests for JWT secret strength enforcement."""

    def test_empty_secret_raises_error(self):
        """Empty JWT secret should raise ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            AuthService("")

    def test_none_secret_raises_error(self):
        """None JWT secret should raise ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            AuthService(None)

    def test_short_secret_raises_error(self):
        """JWT secret shorter than 32 characters should raise ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            AuthService("too_short")

    def test_31_char_secret_raises_error(self):
        """JWT secret of exactly 31 characters should raise ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            AuthService("a" * 31)

    def test_32_char_secret_succeeds(self):
        """JWT secret of exactly 32 characters should succeed."""
        auth_service = AuthService("a" * 32)
        assert auth_service.jwt_secret == "a" * 32

    def test_long_secret_succeeds(self):
        """Long JWT secret should succeed."""
        auth_service = AuthService("a" * 128)
        assert auth_service.jwt_secret == "a" * 128
