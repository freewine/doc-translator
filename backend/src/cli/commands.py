"""
CLI commands for configuration management.

Commands:
- create-admin: Create initial admin user
- create-tables: Create DynamoDB tables
"""
import argparse
import asyncio
import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_repository():
    """Get DynamoDB repository instance."""
    from src.storage.dynamodb_repository import DynamoDBRepository
    return DynamoDBRepository()


async def create_tables_command() -> int:
    """
    Create DynamoDB tables (configuration and users).

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.info("Creating DynamoDB tables...")

    try:
        repo = get_repository()
        await repo.initialize_config_tables()
        logger.info("Configuration tables created successfully!")
        await repo.initialize_users_table()
        logger.info("Users table created successfully!")
        return 0
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return 1


async def create_admin_command(username: str, password: str) -> int:
    """
    Create initial admin user.

    Args:
        username: Admin username.
        password: Admin password.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from datetime import datetime, timezone
    from src.services.user_service import PasswordService

    logger.info(f"Creating admin user '{username}'...")

    try:
        repo = get_repository()

        # Check if user already exists
        existing = await repo.get_user(username)
        if existing:
            logger.info(f"Admin user '{username}' already exists")
            return 0

        # Hash password
        password_hash = PasswordService.hash_password(password)

        # Create user item
        now = datetime.now(timezone.utc)
        user_item = {
            'username': username,
            'password_hash': password_hash,
            'role': 'admin',
            'status': 'pending_password',
            'must_change_password': True,
            'failed_login_count': 0,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }

        await repo.create_user(user_item)
        logger.info(f"Admin user '{username}' created successfully!")
        logger.warning(f"Initial password is set - user must change on first login")

        return 0

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return 1


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for CLI commands.

    Args:
        args: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Configuration management CLI for Doc Translation System"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-tables command
    subparsers.add_parser(
        "create-tables",
        help="Create DynamoDB configuration tables"
    )

    # create-admin command
    admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create initial admin user"
    )
    admin_parser.add_argument(
        "--username",
        "-u",
        required=True,
        help="Admin username"
    )
    admin_parser.add_argument(
        "--password",
        "-p",
        required=True,
        help="Admin password"
    )

    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    # Execute command
    if parsed_args.command == "create-tables":
        return asyncio.run(create_tables_command())
    elif parsed_args.command == "create-admin":
        return asyncio.run(create_admin_command(parsed_args.username, parsed_args.password))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
