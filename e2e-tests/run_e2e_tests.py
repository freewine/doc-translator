#!/usr/bin/env python3
"""
E2E Test Runner

This script provides a unified entry point for running end-to-end tests
with proper environment validation and service checks.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import requests

# Load test configuration
CONFIG_PATH = Path(__file__).parent / "e2e_config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)


class E2ETestRunner:
    """Unified E2E test runner with environment validation."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.backend_url = os.getenv("BACKEND_URL", CONFIG["test_environment"]["backend_url"])
        self.frontend_url = os.getenv("FRONTEND_URL", CONFIG["test_environment"]["frontend_url"])
        self.test_timeout = int(os.getenv("TEST_TIMEOUT", "600"))  # 10 minutes
        
    def check_services(self) -> Dict[str, bool]:
        """Check if required services are running."""
        print("🔍 Checking service availability...")
        
        services = {
            "backend": False,
            "frontend": False
        }
        
        # Check backend
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            services["backend"] = response.status_code == 200
            if services["backend"]:
                print(f"  ✅ Backend service: {self.backend_url}")
            else:
                print(f"  ❌ Backend service: {self.backend_url} (HTTP {response.status_code})")
        except requests.RequestException as e:
            print(f"  ❌ Backend service: {self.backend_url} (Connection failed)")
        
        # Check frontend
        try:
            response = requests.get(self.frontend_url, timeout=5)
            services["frontend"] = response.status_code in [200, 404]  # 404 OK for SPA
            if services["frontend"]:
                print(f"  ✅ Frontend service: {self.frontend_url}")
            else:
                print(f"  ❌ Frontend service: {self.frontend_url} (HTTP {response.status_code})")
        except requests.RequestException as e:
            print(f"  ❌ Frontend service: {self.frontend_url} (Connection failed)")
        
        return services
    
    def check_mcp_configuration(self) -> bool:
        """Check if Chrome DevTools MCP is configured."""
        print("🔍 Checking Chrome DevTools MCP configuration...")
        
        # Check workspace-level config
        mcp_config_paths = [
            Path(".kiro/settings/mcp.json"),
            Path.home() / ".kiro/settings/mcp.json"
        ]
        
        for mcp_config_path in mcp_config_paths:
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)
                    
                    if "chrome-devtools" in config.get("mcpServers", {}):
                        print(f"  ✅ Chrome DevTools MCP configured in {mcp_config_path}")
                        return True
                except (json.JSONDecodeError, KeyError):
                    pass
        
        print("  ⚠️  Chrome DevTools MCP not configured (browser tests will be skipped)")
        return False
    
    def check_test_dependencies(self) -> bool:
        """Check if test dependencies are installed."""
        print("🔍 Checking test dependencies...")
        
        required_packages = ["pytest", "requests", "openpyxl"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n📦 Install missing packages:")
            print(f"   cd e2e-tests && uv sync")
            return False
        
        return True
    
    def run_pytest_tests(self, test_file: Optional[str] = None, markers: Optional[str] = None) -> int:
        """Run pytest-based E2E tests."""
        print("🧪 Running pytest E2E tests...")
        
        cmd = [sys.executable, "-m", "pytest"]
        
        if test_file:
            cmd.append(test_file)
        else:
            cmd.append(".")
        
        cmd.extend(["-v", "--tb=short"])
        
        if markers:
            cmd.extend(["-m", markers])
        
        # Add timeout
        cmd.extend(["--timeout", str(self.test_timeout)])
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=Path(__file__).parent,
                timeout=self.test_timeout
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print(f"❌ Tests timed out after {self.test_timeout} seconds")
            return 1
        except FileNotFoundError:
            print("❌ pytest not found. Install with: cd e2e-tests && uv sync")
            return 1
    
    async def run_chrome_mcp_tests(self) -> int:
        """Run Chrome DevTools MCP automation tests."""
        print("🤖 Running Chrome DevTools MCP tests...")
        
        try:
            from e2e_chrome_runner import ChromeE2ERunner
            
            runner = ChromeE2ERunner()
            await runner.run_all_tests()
            
            # Check if all tests passed
            if hasattr(runner, 'test_results'):
                failed_tests = [name for name, result in runner.test_results.items() 
                              if result.get("status") == "FAILED"]
                return 1 if failed_tests else 0
            
            return 0
            
        except ImportError as e:
            print(f"❌ Failed to import Chrome MCP runner: {e}")
            return 1
        except Exception as e:
            print(f"❌ Chrome MCP tests failed: {e}")
            return 1
    
    def run_api_tests_only(self) -> int:
        """Run API-only tests (no browser automation)."""
        print("🔌 Running API-only tests...")
        return self.run_pytest_tests(markers="api and not browser")
    
    def print_service_startup_help(self):
        """Print help for starting services."""
        print("\n🚀 Service Startup Help:")
        print("=" * 50)
        print("\n📡 Backend Service:")
        print("   cd backend")
        print("   uv run main.py")
        print(f"   Expected URL: {self.backend_url}")
        
        print("\n🌐 Frontend Service:")
        print("   cd frontend")
        print("   npm install  # if not already done")
        print("   npm run dev")
        print(f"   Expected URL: {self.frontend_url}")
        
        print("\n⚙️  Chrome DevTools MCP Setup (optional, for browser tests):")
        print("   Add to .kiro/settings/mcp.json:")
        print('   {')
        print('     "mcpServers": {')
        print('       "chrome-devtools": {')
        print('         "command": "uvx",')
        print('         "args": ["mcp-chrome-devtools@latest"],')
        print('         "disabled": false')
        print('       }')
        print('     }')
        print('   }')
    
    def run_full_validation(self) -> bool:
        """Run full environment validation."""
        print("🔍 Full Environment Validation")
        print("=" * 50)
        
        # Check services
        services = self.check_services()
        services_ok = all(services.values())
        
        # Check MCP (optional)
        mcp_ok = self.check_mcp_configuration()
        
        # Check dependencies
        deps_ok = self.check_test_dependencies()
        
        print(f"\n📊 Validation Summary:")
        print(f"   Services: {'✅' if services_ok else '❌'}")
        print(f"   MCP Config: {'✅' if mcp_ok else '⚠️  (optional)'}")
        print(f"   Dependencies: {'✅' if deps_ok else '❌'}")
        
        # Services and deps are required, MCP is optional
        all_ok = services_ok and deps_ok
        
        if not all_ok:
            print(f"\n❌ Environment validation failed")
            if not services_ok:
                self.print_service_startup_help()
            return False
        
        print(f"\n✅ Environment validation passed")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="E2E Test Runner for Doc Translation System")
    
    parser.add_argument(
        "--mode",
        choices=["full", "api", "chrome", "validate"],
        default="full",
        help="Test mode: full (all tests), api (API only), chrome (browser only), validate (check env)"
    )
    
    parser.add_argument(
        "--test-file",
        help="Specific test file to run"
    )
    
    parser.add_argument(
        "--markers",
        help="Pytest markers to filter tests (e.g., 'e2e', 'api', 'browser')"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip environment validation"
    )
    
    args = parser.parse_args()
    
    runner = E2ETestRunner()
    
    print("🧪 Doc Translation System - E2E Test Runner")
    print("=" * 60)
    print(f"Backend URL: {runner.backend_url}")
    print(f"Frontend URL: {runner.frontend_url}")
    print("=" * 60)
    
    # Validate environment unless skipped
    if not args.skip_validation:
        if not runner.run_full_validation():
            sys.exit(1)
    
    # Run tests based on mode
    exit_code = 0
    
    if args.mode == "validate":
        # Validation already done above
        pass
    
    elif args.mode == "api":
        print(f"\n🔌 Running API-only tests...")
        exit_code = runner.run_api_tests_only()
    
    elif args.mode == "chrome":
        print(f"\n🤖 Running Chrome DevTools MCP tests...")
        exit_code = asyncio.run(runner.run_chrome_mcp_tests())
    
    elif args.mode == "full":
        print(f"\n🧪 Running full E2E test suite...")
        
        # Run pytest tests
        pytest_exit = runner.run_pytest_tests(args.test_file, args.markers)
        
        # Run Chrome MCP tests if pytest passed and MCP is configured
        if pytest_exit == 0 and runner.check_mcp_configuration():
            chrome_exit = asyncio.run(runner.run_chrome_mcp_tests())
            exit_code = chrome_exit
        else:
            exit_code = pytest_exit
    
    # Print final result
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("🎉 All E2E tests completed successfully!")
    else:
        print("❌ Some E2E tests failed. Check output above for details.")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
