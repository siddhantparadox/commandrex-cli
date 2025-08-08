"""
Unit tests for the OpenAI client module.

This module tests the OpenAI API client functionality including:
- Client initialization and validation
- Rate limiting
- Command translation
- Command explanation
- Safety assessment
- Error handling
- Streaming responses
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from openai import APIError, RateLimitError

from commandrex.translator.openai_client import CommandTranslationResult, OpenAIClient


class TestCommandTranslationResult:
    """Test the CommandTranslationResult model."""

    def test_command_translation_result_creation(self):
        """Test creating a CommandTranslationResult."""
        result = CommandTranslationResult(
            command="ls -la",
            explanation="List files with details",
            safety_assessment={"is_safe": True, "risk_level": "low"},
            components=[{"part": "ls", "description": "list command"}],
            is_dangerous=False,
            alternatives=["dir", "ll"],
        )

        assert result.command == "ls -la"
        assert result.explanation == "List files with details"
        assert result.safety_assessment["is_safe"] is True
        assert len(result.components) == 1
        assert result.is_dangerous is False
        assert result.alternatives == ["dir", "ll"]

    def test_command_translation_result_optional_alternatives(self):
        """Test CommandTranslationResult with no alternatives."""
        result = CommandTranslationResult(
            command="pwd",
            explanation="Print working directory",
            safety_assessment={"is_safe": True},
            components=[],
            is_dangerous=False,
        )

        assert result.alternatives is None


class TestOpenAIClientInitialization:
    """Test OpenAI client initialization."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    def test_client_initialization_with_api_key(
        self, mock_async_openai, mock_api_manager
    ):
        """Test client initialization with provided API key."""
        mock_api_manager.is_api_key_valid.return_value = True

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        assert (
            client.api_key == "sk-test123456789012345678901234567890123456789012345678"
        )
        assert client.model == "gpt-5-mini-2025-08-07"
        assert client.min_request_interval == 0.5
        mock_async_openai.assert_called_once_with(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    def test_client_initialization_from_keyring(
        self, mock_async_openai, mock_api_manager
    ):
        """Test client initialization with API key from keyring."""
        mock_api_manager.get_api_key.return_value = (
            "sk-keyring123456789012345678901234567890123456789012345"
        )
        mock_api_manager.is_api_key_valid.return_value = True

        client = OpenAIClient()

        assert (
            client.api_key == "sk-keyring123456789012345678901234567890123456789012345"
        )
        mock_api_manager.get_api_key.assert_called_once()

    @patch("commandrex.translator.openai_client.api_manager")
    def test_client_initialization_no_api_key(self, mock_api_manager):
        """Test client initialization fails without API key."""
        mock_api_manager.get_api_key.return_value = None

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIClient()

    @patch("commandrex.translator.openai_client.api_manager")
    def test_client_initialization_invalid_api_key(self, mock_api_manager):
        """Test client initialization fails with invalid API key."""
        mock_api_manager.is_api_key_valid.return_value = False

        with pytest.raises(ValueError, match="Invalid OpenAI API key format"):
            OpenAIClient(api_key="invalid-key")

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    def test_client_initialization_custom_model(
        self, mock_async_openai, mock_api_manager
    ):
        """Test client initialization with custom model."""
        mock_api_manager.is_api_key_valid.return_value = True

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678",
            model="gpt-4",
        )

        assert client.model == "gpt-4"


class TestRateLimiting:
    """Test rate limiting functionality."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    @patch("commandrex.translator.openai_client.time")
    @patch("commandrex.translator.openai_client.asyncio.sleep")
    async def test_rate_limit_delay(
        self, mock_sleep, mock_time, mock_async_openai, mock_api_manager
    ):
        """Test rate limiting applies delay when needed."""
        mock_api_manager.is_api_key_valid.return_value = True
        mock_time.time.side_effect = [100.2, 100.7]  # Current time, after delay

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )
        client.last_request_time = 100.0  # Set last request time

        await client._handle_rate_limit()

        # Check that sleep was called with approximately 0.3 seconds
        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0]
        assert abs(call_args[0] - 0.3) < 0.01  # Allow for floating point precision
        assert client.last_request_time == 100.7

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    @patch("commandrex.translator.openai_client.time")
    @patch("commandrex.translator.openai_client.asyncio.sleep")
    async def test_rate_limit_no_delay_needed(
        self, mock_sleep, mock_time, mock_async_openai, mock_api_manager
    ):
        """Test rate limiting doesn't delay when enough time has passed."""
        mock_api_manager.is_api_key_valid.return_value = True
        mock_time.time.side_effect = [101.0, 101.5]  # Current time, after check

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )
        client.last_request_time = 100.0  # More than 0.5 seconds ago

        await client._handle_rate_limit()

        mock_sleep.assert_not_called()
        assert client.last_request_time == 101.5


class TestTranslateToCommand:
    """Test command translation functionality."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_success(
        self, mock_async_openai, mock_api_manager
    ):
        """Test successful command translation."""
        mock_api_manager.is_api_key_valid.return_value = True

        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "command": "ls -la",
                "explanation": "List files with details",
                "safety_assessment": {
                    "is_safe": True,
                    "risk_level": "low",
                    "concerns": [],
                },
                "components": [{"part": "ls", "description": "list command"}],
                "is_dangerous": False,
                "alternatives": ["dir"],
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.translate_to_command(
                "list files", {"platform": "linux", "shell": "bash"}
            )

        assert isinstance(result, CommandTranslationResult)
        assert result.command == "ls -la"
        assert result.explanation == "List files with details"
        assert result.is_dangerous is False
        assert len(result.alternatives) == 1

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_with_streaming(
        self, mock_async_openai, mock_api_manager
    ):
        """Test command translation with streaming callback."""
        mock_api_manager.is_api_key_valid.return_value = True

        # Mock streaming response
        response_chunks = [
            '{"command": "ls -la",',
            ' "explanation": "List files",',
            ' "safety_assessment": {"is_safe": true},',
            ' "components": [], "is_dangerous": false}',
        ]

        mock_chunks = []
        for chunk_content in response_chunks:
            mock_chunk = Mock()
            mock_chunk.choices = [Mock()]
            mock_chunk.choices[0].delta.content = chunk_content
            mock_chunks.append(mock_chunk)

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        callback_chunks = []

        def stream_callback(chunk):
            callback_chunks.append(chunk)

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.translate_to_command(
                "list files", {"platform": "linux"}, stream_callback=stream_callback
            )

        assert isinstance(result, CommandTranslationResult)
        assert result.command == "ls -la"
        assert callback_chunks == response_chunks

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_json_decode_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of JSON decode errors."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json"

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Failed to parse API response"):
                await client.translate_to_command("test", {})

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_rate_limit_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of rate limit errors."""
        mock_api_manager.is_api_key_valid.return_value = True

        # Create a mock response for RateLimitError
        mock_response = Mock()
        mock_response.request = Mock()

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded", response=mock_response, body=None
            )
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="OpenAI API rate limit exceeded"):
                await client.translate_to_command("test", {})

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_api_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of API errors."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_client = Mock()
        # Create a mock request for APIError
        mock_request = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIError("API error", request=mock_request, body=None)
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Error communicating with OpenAI API"):
                await client.translate_to_command("test", {})

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_http_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of HTTP errors."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=httpx.HTTPError("Network error")
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Network error during API request"):
                await client.translate_to_command("test", {})

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_translate_to_command_unexpected_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of unexpected errors."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(
                ValueError, match="Unexpected error during command translation"
            ):
                await client.translate_to_command("test", {})


class TestExplainCommand:
    """Test command explanation functionality."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_explain_command_success(self, mock_async_openai, mock_api_manager):
        """Test successful command explanation."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "explanation": "Lists files in the current directory",
                "components": [{"part": "ls", "description": "list command"}],
                "examples": ["ls -l", "ls -a"],
                "related_commands": ["dir", "find"],
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.explain_command("ls")

        assert result["explanation"] == "Lists files in the current directory"
        assert len(result["components"]) == 1
        assert len(result["examples"]) == 2
        assert len(result["related_commands"]) == 2

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_explain_command_json_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of JSON errors in explanation."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json"

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Failed to parse API response"):
                await client.explain_command("ls")

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_explain_command_general_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of general errors in explanation."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("General error")
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Error explaining command"):
                await client.explain_command("ls")


class TestAssessCommandSafety:
    """Test command safety assessment functionality."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_assess_command_safety_success(
        self, mock_async_openai, mock_api_manager
    ):
        """Test successful safety assessment."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "is_safe": True,
                "risk_level": "low",
                "concerns": [],
                "recommendations": ["Use with caution"],
                "safer_alternatives": ["ls -l"],
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.assess_command_safety("ls")

        assert result["is_safe"] is True
        assert result["risk_level"] == "low"
        assert len(result["concerns"]) == 0
        assert len(result["recommendations"]) == 1
        assert len(result["safer_alternatives"]) == 1

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_assess_command_safety_dangerous(
        self, mock_async_openai, mock_api_manager
    ):
        """Test safety assessment for dangerous command."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "is_safe": False,
                "risk_level": "high",
                "concerns": ["Deletes all files", "Irreversible"],
                "recommendations": ["Never run this command"],
                "safer_alternatives": ["rm specific_file"],
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.assess_command_safety("rm -rf /")

        assert result["is_safe"] is False
        assert result["risk_level"] == "high"
        assert len(result["concerns"]) == 2
        assert "Deletes all files" in result["concerns"]

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_assess_command_safety_json_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of JSON errors in safety assessment."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json"

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Failed to parse API response"):
                await client.assess_command_safety("ls")

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_assess_command_safety_general_error(
        self, mock_async_openai, mock_api_manager
    ):
        """Test handling of general errors in safety assessment."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("General error")
        )
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Error assessing command safety"):
                await client.assess_command_safety("ls")


class TestOpenAIClientEdgeCases:
    """Test edge cases and error conditions."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_streaming_with_none_content(
        self, mock_async_openai, mock_api_manager
    ):
        """Test streaming response with None content chunks."""
        mock_api_manager.is_api_key_valid.return_value = True

        # Mock streaming response with some None content
        mock_chunks = []

        # First chunk with None content
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta.content = None
        mock_chunks.append(mock_chunk1)

        # Second chunk with actual content
        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta.content = (
            '{"command": "ls", "explanation": "test", "safety_assessment": {}, '
            '"components": [], "is_dangerous": false}'
        )
        mock_chunks.append(mock_chunk2)

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        callback_chunks = []

        def stream_callback(chunk):
            callback_chunks.append(chunk)

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.translate_to_command(
                "list files", {"platform": "linux"}, stream_callback=stream_callback
            )

        assert isinstance(result, CommandTranslationResult)
        assert result.command == "ls"
        # Only the non-None chunk should be in callback
        assert len(callback_chunks) == 1

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_missing_response_fields(self, mock_async_openai, mock_api_manager):
        """Test handling of missing fields in API response."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "command": "ls",
                # Missing other required fields
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.translate_to_command("test", {})

        # Should handle missing fields gracefully with defaults
        assert result.command == "ls"
        assert result.explanation == ""
        assert result.safety_assessment == {}
        assert result.components == []
        assert result.is_dangerous is False
        assert result.alternatives == []


class TestOpenAIClientIntegration:
    """Integration tests for OpenAI client functionality."""

    @patch("commandrex.translator.openai_client.api_manager")
    @patch("commandrex.translator.openai_client.AsyncOpenAI")
    async def test_full_translation_workflow(self, mock_async_openai, mock_api_manager):
        """Test complete translation workflow."""
        mock_api_manager.is_api_key_valid.return_value = True

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "command": "find . -name '*.py' -type f",
                "explanation": "Find all Python files in current directory and "
                "subdirectories",
                "safety_assessment": {
                    "is_safe": True,
                    "risk_level": "low",
                    "concerns": [],
                },
                "components": [
                    {"part": "find", "description": "Search for files"},
                    {"part": ".", "description": "Current directory"},
                    {"part": "-name '*.py'", "description": "Files ending in .py"},
                    {"part": "-type f", "description": "Regular files only"},
                ],
                "is_dangerous": False,
                "alternatives": ["ls *.py", "locate *.py"],
            }
        )

        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_client

        client = OpenAIClient(
            api_key="sk-test123456789012345678901234567890123456789012345678"
        )

        with patch.object(client, "_handle_rate_limit", new_callable=AsyncMock):
            result = await client.translate_to_command(
                "find all python files", {"platform": "linux", "shell": "bash"}
            )

        assert result.command == "find . -name '*.py' -type f"
        assert "Python files" in result.explanation
        assert result.safety_assessment["is_safe"] is True
        assert len(result.components) == 4
        assert result.is_dangerous is False
        assert len(result.alternatives) == 2

        # Verify the API was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-5-mini-2025-08-07"
        assert call_args[1]["response_format"] == {"type": "json_object"}
        assert len(call_args[1]["messages"]) == 3  # system, system context, user
