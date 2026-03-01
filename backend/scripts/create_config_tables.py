#!/usr/bin/env python3
"""
Script to create DynamoDB tables for config storage (Unit-2).

Creates the following tables:
- doc_translation_language_pairs: User language pair configurations
- doc_translation_user_settings: User preference settings
- doc_translation_global_config: System-level global configuration

Usage:
    uv run python scripts/create_config_tables.py [--region REGION]
"""
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Table definitions
TABLES = {
    "doc_translation_language_pairs": {
        "KeySchema": [
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "id", "AttributeType": "S"},
        ],
    },
    "doc_translation_user_settings": {
        "KeySchema": [
            {"AttributeName": "user_id", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
    },
    "doc_translation_global_config": {
        "KeySchema": [
            {"AttributeName": "config_key", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "config_key", "AttributeType": "S"},
        ],
    },
}


def create_table(dynamodb, table_name: str, table_config: dict) -> bool:
    """
    Create a DynamoDB table.
    
    Args:
        dynamodb: DynamoDB client
        table_name: Name of the table to create
        table_config: Table configuration (KeySchema, AttributeDefinitions)
        
    Returns:
        True if created or already exists, False on error
    """
    try:
        # Check if table already exists
        dynamodb.describe_table(TableName=table_name)
        logger.info(f"Table '{table_name}' already exists")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            logger.error(f"Error checking table '{table_name}': {e}")
            return False
    
    # Create the table
    try:
        logger.info(f"Creating table '{table_name}'...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=table_config["KeySchema"],
            AttributeDefinitions=table_config["AttributeDefinitions"],
            BillingMode="PAY_PER_REQUEST",
        )
        
        # Wait for table to be active
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        logger.info(f"Table '{table_name}' created successfully")
        return True
        
    except ClientError as e:
        logger.error(f"Error creating table '{table_name}': {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create DynamoDB tables for config storage"
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2)"
    )
    args = parser.parse_args()
    
    logger.info(f"Creating config tables in region: {args.region}")
    
    # Create DynamoDB client
    dynamodb = boto3.client('dynamodb', region_name=args.region)
    
    # Create all tables
    success_count = 0
    for table_name, table_config in TABLES.items():
        if create_table(dynamodb, table_name, table_config):
            success_count += 1
    
    # Summary
    total = len(TABLES)
    logger.info(f"\nSummary: {success_count}/{total} tables ready")
    
    if success_count == total:
        logger.info("All config tables are ready!")
        return 0
    else:
        logger.error("Some tables failed to create")
        return 1


if __name__ == "__main__":
    sys.exit(main())
