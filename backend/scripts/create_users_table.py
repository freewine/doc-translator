#!/usr/bin/env python3
"""
DynamoDB Users Table Creation Script.

This script creates the DynamoDB table for user management with the required
schema and Global Secondary Index (GSI) for efficient queries.

Table Schema:
- Partition Key: username (String)
- Attributes: role, status, password_hash, must_change_password, 
              failed_login_count, created_at, updated_at, deleted_at

GSI: role-index
- Partition Key: role (String)
- Sort Key: username (String)
- Purpose: Query users by role efficiently

Usage:
    uv run python scripts/create_users_table.py [--region REGION] [--table-name TABLE_NAME]

Examples:
    # Create table with defaults (us-west-2, doc-translator-users)
    uv run python scripts/create_users_table.py
    
    # Create table in specific region
    uv run python scripts/create_users_table.py --region us-east-1
    
    # Create table with custom name
    uv run python scripts/create_users_table.py --table-name my-app-users
"""

import argparse
import logging
import os
import secrets
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_REGION = os.getenv("AWS_REGION", "us-west-2")
DEFAULT_TABLE_NAME = os.getenv("USERS_TABLE_NAME", "doc-translator-users")


def create_users_table(
    region: str = DEFAULT_REGION,
    table_name: str = DEFAULT_TABLE_NAME,
    wait_for_active: bool = True
) -> bool:
    """
    Create the DynamoDB users table with GSI.
    
    Args:
        region: AWS region for the table
        table_name: Name of the DynamoDB table
        wait_for_active: Whether to wait for table to become active
        
    Returns:
        True if table was created successfully, False otherwise
    """
    logger.info(f"Creating DynamoDB table '{table_name}' in region '{region}'...")
    
    try:
        dynamodb = boto3.client('dynamodb', region_name=region)
        
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            logger.info(f"Table '{table_name}' already exists (status: {status})")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table with GSI
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'username',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'role',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'role-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'role',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'username',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand capacity
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'doc-translator'
                },
                {
                    'Key': 'Component',
                    'Value': 'user-management'
                }
            ]
        )
        
        logger.info(f"Table creation initiated: {response['TableDescription']['TableArn']}")
        
        if wait_for_active:
            logger.info("Waiting for table to become active...")
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(
                TableName=table_name,
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': 25
                }
            )
            logger.info(f"Table '{table_name}' is now active")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to create table: {error_code} - {error_message}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def create_initial_admin_user(
    region: str = DEFAULT_REGION,
    table_name: str = DEFAULT_TABLE_NAME,
    username: str = "admin",
    password: str | None = None,
) -> bool:
    """
    Create an initial admin user in the users table.
    
    Args:
        region: AWS region for the table
        table_name: Name of the DynamoDB table
        username: Admin username
        password: Admin password (will be hashed)
        
    Returns:
        True if user was created successfully, False otherwise
    """
    if password is None:
        password = secrets.token_urlsafe(12)
    logger.info(f"Creating initial admin user '{username}'...")

    try:
        # Import UserService for password hashing
        from src.services.user_service import PasswordService
        from src.storage.dynamodb_repository import DynamoDBRepository
        from datetime import datetime, timezone

        # Hash the password
        password_hash = PasswordService.hash_password(password)
        
        # Create repository and add user
        # Note: Region is determined by boto3 default chain (env vars, config file, instance metadata)
        repository = DynamoDBRepository()
        
        # Check if user already exists
        existing = repository.get_user(username)
        if existing:
            logger.info(f"Admin user '{username}' already exists")
            return True
        
        # Create user item
        now = datetime.now(timezone.utc)
        user_item = {
            'username': username,
            'password_hash': password_hash,
            'role': 'admin',
            'status': 'pending_password',  # Require password change on first login
            'must_change_password': True,
            'failed_login_count': 0,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }
        
        repository.create_user(user_item)
        logger.info(f"Admin user '{username}' created successfully")
        logger.warning(f"Temporary password: {password}")
        logger.warning("Change this password immediately! It will not be shown again.")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Create DynamoDB users table for Doc Translation System'
    )
    parser.add_argument(
        '--region',
        default=DEFAULT_REGION,
        help=f'AWS region (default: {DEFAULT_REGION})'
    )
    parser.add_argument(
        '--table-name',
        default=DEFAULT_TABLE_NAME,
        help=f'DynamoDB table name (default: {DEFAULT_TABLE_NAME})'
    )
    parser.add_argument(
        '--create-admin',
        action='store_true',
        help='Create initial admin user after table creation'
    )
    parser.add_argument(
        '--admin-username',
        default='admin',
        help='Admin username (default: admin)'
    )
    parser.add_argument(
        '--admin-password',
        default=None,
        help='Admin password (default: randomly generated)'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Do not wait for table to become active'
    )
    
    args = parser.parse_args()
    
    # Create table
    success = create_users_table(
        region=args.region,
        table_name=args.table_name,
        wait_for_active=not args.no_wait
    )
    
    if not success:
        sys.exit(1)
    
    # Create initial admin user if requested
    if args.create_admin:
        success = create_initial_admin_user(
            region=args.region,
            table_name=args.table_name,
            username=args.admin_username,
            password=args.admin_password
        )
        if not success:
            sys.exit(1)
    
    logger.info("Setup completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
