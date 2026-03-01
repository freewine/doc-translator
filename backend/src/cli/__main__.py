"""
CLI entry point for running as a module.

Usage:
    python -m src.cli create-tables
    python -m src.cli create-admin --username <user> --password <pass>
"""
import sys
from src.cli.commands import main

if __name__ == "__main__":
    sys.exit(main())
