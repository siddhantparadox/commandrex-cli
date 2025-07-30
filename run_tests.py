"""
Test runner script for CommandRex.

This script provides a convenient way to run tests with different configurations
and generate coverage reports.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n🔄 {description}")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    
    print("✅ Command completed successfully")
    if result.stdout:
        print(result.stdout)
    
    return True


def install_dependencies():
    """Install test dependencies."""
    return run_command([
        sys.executable, "-m", "pip", "install", "-e", ".[test]"
    ], "Installing test dependencies")


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/unit"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=commandrex", "--cov-report=term-missing"])
    
    cmd.append("-m")
    cmd.append("unit")
    
    return run_command(cmd, "Running unit tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/integration"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.append("-m")
    cmd.append("integration")
    
    return run_command(cmd, "Running integration tests")


def run_all_tests(verbose=False, coverage=False):
    """Run all tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=commandrex",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml"
        ])
    
    return run_command(cmd, "Running all tests")


def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = [sys.executable, "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, f"Running specific test: {test_path}")


def generate_coverage_report():
    """Generate HTML coverage report."""
    cmd = [sys.executable, "-m", "pytest", "tests/", 
           "--cov=commandrex", "--cov-report=html:htmlcov"]
    
    success = run_command(cmd, "Generating coverage report")
    
    if success:
        html_report = Path("htmlcov/index.html")
        if html_report.exists():
            print(f"📊 Coverage report generated: {html_report.absolute()}")
        else:
            print("⚠️  Coverage report not found")
    
    return success


def lint_code():
    """Run code linting."""
    success = True
    
    # Run ruff
    if not run_command([sys.executable, "-m", "ruff", "check", "commandrex/"], "Running ruff linter"):
        success = False
    
    # Run black check
    if not run_command([sys.executable, "-m", "black", "--check", "commandrex/"], "Checking code formatting"):
        success = False
    
    return success


def format_code():
    """Format code with black."""
    return run_command([sys.executable, "-m", "black", "commandrex/"], "Formatting code with black")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="CommandRex Test Runner")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", help="Run specific test file or function")
    
    args = parser.parse_args()
    
    # If no specific action is specified, run all tests
    if not any([args.install, args.unit, args.integration, args.all, 
                args.coverage, args.lint, args.format, args.test]):
        args.all = True
    
    success = True
    
    try:
        if args.install:
            success &= install_dependencies()
        
        if args.lint:
            success &= lint_code()
        
        if args.format:
            success &= format_code()
        
        if args.unit:
            success &= run_unit_tests(verbose=args.verbose, coverage=args.coverage)
        
        if args.integration:
            success &= run_integration_tests(verbose=args.verbose)
        
        if args.all:
            success &= run_all_tests(verbose=args.verbose, coverage=args.coverage)
        
        if args.coverage and not (args.unit or args.all):
            success &= generate_coverage_report()
        
        if args.test:
            success &= run_specific_test(args.test, verbose=args.verbose)
        
        if success:
            print("\n🎉 All operations completed successfully!")
            return 0
        else:
            print("\n❌ Some operations failed!")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())