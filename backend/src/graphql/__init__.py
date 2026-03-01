"""
GraphQL module for the Doc Translation System.

This module provides the GraphQL schema and types for the API.
"""
from .schema import (
    schema,
    Query,
    Mutation,
    User,
    AuthPayload,
    LanguagePair,
    TranslationJob,
    FileProgress,
    FileError,
    FileUpload,
    JobStatus,
)
from .resolvers import (
    ResolverContext,
    AuthenticationError,
    ValidationError,
)

__all__ = [
    "schema",
    "Query",
    "Mutation",
    "User",
    "AuthPayload",
    "LanguagePair",
    "TranslationJob",
    "FileProgress",
    "FileError",
    "FileUpload",
    "JobStatus",
    "ResolverContext",
    "AuthenticationError",
    "ValidationError",
]
