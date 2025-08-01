"""
Shared test fixtures for CommandRex tests.

This module contains pytest fixtures that are shared across all test modules,
including mocks for external services, test data, and common test utilities.
"""

import json
import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from faker import Faker

# Import CommandRex modules for testing
from commandrex.executor import platform_utils
from commandrex.translator.openai_client import CommandTranslationResult

fake = Faker()


# ============================================================================
# API Key Fixtures
# ============================================================================


@pytest.fixture
def valid_api_key() -> str:
    """Return a valid OpenAI API key format for testing."""
    return "sk-" + "a" * 48  # 51 characters total


@pytest.fixture
def invalid_api_key() -> str:
    """Return an invalid API key format for testing."""
    return "invalid-key-format"


@pytest.fixture
def mock_keyring():
    """Mock the keyring module for testing."""
    with (
        patch("keyring.get_password") as mock_get,
        patch("keyring.set_password") as mock_set,
        patch("keyring.delete_password") as mock_delete,
    ):
        # Default behavior: no key stored
        mock_get.return_value = None
        mock_set.return_value = None
        mock_delete.return_value = None

        yield {"get": mock_get, "set": mock_set, "delete": mock_delete}


# ============================================================================
# OpenAI API Fixtures
# ============================================================================


@pytest.fixture
def mock_openai_response() -> Dict[str, Any]:
    """Return a mock OpenAI API response for command translation."""
    return {
        "command": "ls -la",
        "explanation": "List all files in the current directory with detailed "
        "information",
        "safety_assessment": {"is_safe": True, "concerns": [], "risk_level": "low"},
        "components": [
            {"part": "ls", "description": "List directory contents"},
            {"part": "-la", "description": "Show all files with detailed information"},
        ],
        "is_dangerous": False,
        "alternatives": ["dir /a", "Get-ChildItem -Force"],
    }


@pytest.fixture
def mock_dangerous_command_response() -> Dict[str, Any]:
    """Return a mock OpenAI API response for a dangerous command."""
    return {
        "command": "rm -rf /",
        "explanation": "Recursively delete all files starting from root directory",
        "safety_assessment": {
            "is_safe": False,
            "concerns": [
                "Recursive deletion",
                "System-wide deletion",
                "No confirmation",
            ],
            "risk_level": "high",
        },
        "components": [
            {"part": "rm", "description": "Remove files and directories"},
            {"part": "-rf", "description": "Recursive and force deletion flags"},
        ],
        "is_dangerous": True,
        "alternatives": ["rm -i specific_file", "trash specific_file"],
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    client.translate_to_command = AsyncMock()
    client.explain_command = AsyncMock()
    client.assess_command_safety = AsyncMock()
    return client


@pytest.fixture
def mock_command_translation_result(mock_openai_response) -> CommandTranslationResult:
    """Return a mock CommandTranslationResult object."""
    return CommandTranslationResult(**mock_openai_response)


# ============================================================================
# System/Platform Fixtures
# ============================================================================


@pytest.fixture
def mock_windows_platform():
    """Mock Windows platform detection."""
    with (
        patch.object(platform_utils, "is_windows", return_value=True),
        patch.object(platform_utils, "get_platform_info") as mock_info,
    ):
        mock_info.return_value = {
            "os_name": "Windows",
            "os_version": "10.0.19041",
            "shell_name": "cmd",
            "shell_version": "10.0.19041.1",
            "python_version": "3.11.0",
        }
        yield mock_info


@pytest.fixture
def mock_unix_platform():
    """Mock Unix/Linux platform detection."""
    with (
        patch.object(platform_utils, "is_windows", return_value=False),
        patch.object(platform_utils, "get_platform_info") as mock_info,
    ):
        mock_info.return_value = {
            "os_name": "Linux",
            "os_version": "5.15.0",
            "shell_name": "bash",
            "shell_version": "5.1.16",
            "python_version": "3.11.0",
        }
        yield mock_info


@pytest.fixture
def mock_shell_detection():
    """Mock shell detection functionality."""
    with patch.object(platform_utils, "detect_shell") as mock_detect:
        mock_detect.return_value = (
            "bash",
            "5.1.16",
            {
                "supports_colors": True,
                "supports_unicode": True,
                "supports_job_control": True,
            },
        )
        yield mock_detect


# ============================================================================
# Command Execution Fixtures
# ============================================================================


@pytest.fixture
def mock_successful_command_result():
    """Mock successful command execution result."""
    result = Mock()
    result.success = True
    result.return_code = 0
    result.stdout = "Command executed successfully"
    result.stderr = ""
    return result


@pytest.fixture
def mock_failed_command_result():
    """Mock failed command execution result."""
    result = Mock()
    result.success = False
    result.return_code = 1
    result.stdout = ""
    result.stderr = "Command failed"
    return result


@pytest.fixture
def mock_shell_manager():
    """Mock shell manager for testing."""
    manager = Mock()
    manager.execute_command_safely = AsyncMock()
    return manager


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_commands() -> List[Dict[str, Any]]:
    """Return sample commands for testing."""
    return [
        {
            "query": "list all files",
            "expected_command": "ls -la",
            "is_dangerous": False,
        },
        {
            "query": "delete all files in current directory",
            "expected_command": "rm -rf *",
            "is_dangerous": True,
        },
        {
            "query": "show running processes",
            "expected_command": "ps aux",
            "is_dangerous": False,
        },
        {
            "query": "find large files",
            "expected_command": "find . -type f -size +100M",
            "is_dangerous": False,
        },
    ]


@pytest.fixture
def sample_system_info() -> Dict[str, Any]:
    """Return sample system information for testing."""
    return {
        "os_name": "Linux",
        "os_version": "5.15.0-56-generic",
        "shell_name": "bash",
        "shell_version": "5.1.16(1)-release",
        "python_version": "3.11.0",
        "architecture": "x86_64",
        "user": "testuser",
        "home_directory": "/home/testuser",
        "current_directory": "/home/testuser/projects",
    }


# ============================================================================
# Temporary File Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config = {
            "api_key": "test-key",
            "model": "gpt-4.1-mini-2025-04-14",
            "debug": False,
        }
        json.dump(config, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def clean_environment():
    """Provide a clean environment without API keys."""
    original_env = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    yield

    if original_env:
        os.environ["OPENAI_API_KEY"] = original_env


@pytest.fixture
def mock_env_api_key(valid_api_key):
    """Mock environment variable with API key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": valid_api_key}):
        yield valid_api_key


# ============================================================================
# Async Fixtures
# ============================================================================


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Error Simulation Fixtures
# ============================================================================


@pytest.fixture
def mock_network_error():
    """Mock network error for testing error handling."""
    import httpx

    return httpx.NetworkError("Connection failed")


@pytest.fixture
def mock_api_error():
    """Mock OpenAI API error for testing."""
    from openai import APIError

    return APIError("API request failed")


@pytest.fixture
def mock_rate_limit_error():
    """Mock rate limit error for testing."""
    from openai import RateLimitError

    return RateLimitError("Rate limit exceeded")


# ============================================================================
# Utility Functions
# ============================================================================


def create_mock_response(content: str, status_code: int = 200):
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.text = content
    response.json.return_value = json.loads(content) if content else {}
    return response


def assert_command_components(
    components: List[Dict[str, str]], expected_parts: List[str]
):
    """Assert that command components contain expected parts."""
    component_parts = [comp["part"] for comp in components]
    for part in expected_parts:
        assert part in component_parts, (
            f"Expected part '{part}' not found in components"
        )


# ============================================================================
# Parametrized Fixtures
# ============================================================================


@pytest.fixture(params=["windows", "linux", "macos"])
def platform_type(request):
    """Parametrized fixture for different platform types."""
    return request.param


@pytest.fixture(params=["bash", "zsh", "fish", "cmd", "powershell"])
def shell_type(request):
    """Parametrized fixture for different shell types."""
    return request.param


@pytest.fixture(params=[True, False])
def debug_mode(request):
    """Parametrized fixture for debug mode testing."""
    return request.param
