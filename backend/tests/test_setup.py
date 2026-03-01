"""Test to verify the test infrastructure is working."""

import sys


def test_python_version():
    """Verify Python version is 3.9 or higher."""
    assert sys.version_info >= (3, 9), f"Python 3.9+ required, got {sys.version}"


def test_imports():
    """Verify all required packages can be imported."""
    import strawberry
    import uvicorn
    import jwt
    import bcrypt
    import openpyxl
    import boto3
    import PIL
    import hypothesis
    import pytest
    import dotenv
    
    # If we get here, all imports succeeded
    assert True
