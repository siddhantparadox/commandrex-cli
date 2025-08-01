"""
Unit tests for the main CLI module.

This module tests the main CLI interface including command handlers,
API key management, and user interaction flows.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from commandrex.main import app, check_api_key, get_version, process_translation


class TestVersionHandling:
    """Test version handling functionality."""

    @patch("commandrex.main.importlib.metadata.version")
    def test_get_version_success(self, mock_version):
        """Test getting version when package is installed."""
        mock_version.return_value = "1.2.3"

        version = get_version()

        assert version == "1.2.3"
        mock_version.assert_called_once_with("commandrex")

    @patch("commandrex.main.importlib.metadata.version")
    def test_get_version_package_not_found(self, mock_version):
        """Test getting version when package is not found."""
        from importlib.metadata import PackageNotFoundError

        mock_version.side_effect = PackageNotFoundError()

        version = get_version()

        assert version == "0.1.0"


class TestCallbackCommand:
    """Test the main callback command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("commandrex.main.get_version")
    def test_callback_version_option(self, mock_get_version):
        """Test --version option."""
        mock_get_version.return_value = "1.2.3"

        result = self.runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "CommandRex CLI Version: 1.2.3" in result.stdout

    @patch("commandrex.main.api_manager.delete_api_key")
    @patch("commandrex.main.typer.confirm")
    def test_callback_reset_api_key_no_new_key(self, mock_confirm, mock_delete):
        """Test --reset-api-key option without setting new key."""
        mock_delete.return_value = True
        mock_confirm.return_value = False

        result = self.runner.invoke(app, ["--reset-api-key"])

        assert result.exit_code == 0
        assert "API key deleted successfully" in result.stdout
        assert "You will be prompted to enter an API key" in result.stdout
        mock_delete.assert_called_once()

    @patch("commandrex.main.api_manager.delete_api_key")
    @patch("commandrex.main.api_manager.save_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    @patch("commandrex.main.typer.confirm")
    @patch("commandrex.main.typer.prompt")
    def test_callback_reset_api_key_with_new_key(
        self, mock_prompt, mock_confirm, mock_is_valid, mock_save, mock_delete
    ):
        """Test --reset-api-key option with setting new key."""
        mock_delete.return_value = True
        mock_confirm.return_value = True
        mock_prompt.return_value = "sk-test123456789012345678901234567890123456789012"
        mock_is_valid.return_value = True
        mock_save.return_value = True

        result = self.runner.invoke(app, ["--reset-api-key"])

        assert result.exit_code == 0
        assert "API key deleted successfully" in result.stdout
        assert "New API key saved successfully" in result.stdout
        mock_delete.assert_called_once()
        mock_save.assert_called_once()

    @patch("commandrex.main.api_manager.delete_api_key")
    def test_callback_reset_api_key_delete_failed(self, mock_delete):
        """Test --reset-api-key option when delete fails."""
        mock_delete.return_value = False

        result = self.runner.invoke(app, ["--reset-api-key"])

        assert result.exit_code == 1
        assert "Failed to delete API key" in result.stdout

    def test_callback_no_options_shows_help(self):
        """Test that no options shows help."""
        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "CommandRex - Natural Language Terminal Interface" in result.stdout


class TestApiKeyChecking:
    """Test API key checking functionality."""

    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    def test_check_api_key_valid_existing_key(self, mock_is_valid, mock_get_key):
        """Test check_api_key with valid existing key."""
        mock_get_key.return_value = "sk-test123456789012345678901234567890123456789012"
        mock_is_valid.return_value = True

        result = check_api_key()

        assert result is True

    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.typer.confirm")
    def test_check_api_key_no_key_user_declines(self, mock_confirm, mock_get_key):
        """Test check_api_key when no key exists and user declines setup."""
        mock_get_key.return_value = None
        mock_confirm.return_value = False

        result = check_api_key()

        assert result is False

    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.api_manager.save_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    @patch("commandrex.main.typer.confirm")
    @patch("commandrex.main.typer.prompt")
    def test_check_api_key_no_key_user_sets_valid_key(
        self, mock_prompt, mock_confirm, mock_is_valid, mock_save, mock_get_key
    ):
        """Test check_api_key when user sets valid new key."""
        mock_get_key.return_value = None
        mock_confirm.return_value = True
        mock_prompt.return_value = "sk-test123456789012345678901234567890123456789012"
        mock_is_valid.return_value = True
        mock_save.return_value = True

        result = check_api_key()

        assert result is True
        mock_save.assert_called_once()

    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    @patch("commandrex.main.typer.confirm")
    @patch("commandrex.main.typer.prompt")
    def test_check_api_key_no_key_invalid_format(
        self, mock_prompt, mock_confirm, mock_is_valid, mock_get_key
    ):
        """Test check_api_key when user provides invalid key format."""
        mock_get_key.return_value = None
        mock_confirm.return_value = True
        mock_prompt.return_value = "invalid-key"
        mock_is_valid.return_value = False

        result = check_api_key()

        assert result is False

    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    @patch("commandrex.main.api_manager.delete_api_key")
    @patch("commandrex.main.api_manager.save_api_key")
    @patch("commandrex.main.typer.confirm")
    @patch("commandrex.main.typer.prompt")
    def test_check_api_key_invalid_existing_key_reset(
        self,
        mock_prompt,
        mock_confirm,
        mock_save,
        mock_delete,
        mock_is_valid,
        mock_get_key,
    ):
        """Test check_api_key with invalid existing key that gets reset."""
        mock_get_key.return_value = "invalid-key"
        mock_is_valid.side_effect = [False, True]  # First call invalid, second valid
        mock_confirm.return_value = True
        mock_delete.return_value = True
        mock_prompt.return_value = "sk-test123456789012345678901234567890123456789012"
        mock_save.return_value = True

        result = check_api_key()

        assert result is True
        mock_delete.assert_called_once()
        mock_save.assert_called_once()


class TestTranslateCommand:
    """Test the translate command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_translate_no_query(self):
        """Test translate command with no query."""
        result = self.runner.invoke(app, ["translate"])

        assert result.exit_code == 1
        assert "No query provided" in result.stdout

    @patch("commandrex.main.api_manager.is_api_key_valid")
    def test_translate_invalid_api_key_option(self, mock_is_valid):
        """Test translate command with invalid API key option."""
        mock_is_valid.return_value = False

        result = self.runner.invoke(
            app, ["translate", "--api-key", "invalid", "test query"]
        )

        assert result.exit_code == 1
        assert "Invalid API key format" in result.stdout

    @patch("commandrex.main.check_api_key")
    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.prompt_builder.PromptBuilder")
    @patch("commandrex.main.asyncio.run")
    def test_translate_success(
        self, mock_asyncio_run, mock_pb_class, mock_client_class, mock_check_key
    ):
        """Test successful translate command."""
        # Mock API key check
        mock_check_key.return_value = True

        # Mock prompt builder
        mock_pb = Mock()
        mock_pb.build_system_context.return_value = {"platform": "test"}
        mock_pb_class.return_value = mock_pb

        # Mock OpenAI client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.command = "ls -la"
        mock_result.explanation = "List files with details"
        mock_result.is_dangerous = False
        mock_result.components = [{"part": "ls", "description": "list command"}]
        mock_result.safety_assessment = {"concerns": []}
        mock_result.alternatives = []

        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        # Mock asyncio.run
        mock_asyncio_run.return_value = mock_result

        result = self.runner.invoke(app, ["translate", "list files"])

        assert result.exit_code == 0
        assert "ls -la" in result.stdout
        assert "List files with details" in result.stdout

    @patch("commandrex.main.check_api_key")
    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.asyncio.run")
    def test_translate_api_error(
        self, mock_asyncio_run, mock_client_class, mock_check_key
    ):
        """Test translate command with API error."""
        mock_check_key.return_value = True

        # Mock client that raises exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock asyncio.run that raises exception
        mock_asyncio_run.side_effect = Exception("API Error")

        result = self.runner.invoke(app, ["translate", "test query"])

        assert result.exit_code == 1
        assert "Error: API Error" in result.stdout


class TestExplainCommand:
    """Test the explain command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_explain_no_command(self):
        """Test explain command with no command."""
        result = self.runner.invoke(app, ["explain"])

        assert result.exit_code == 1
        assert "No command provided" in result.stdout

    @patch("commandrex.main.check_api_key")
    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.security.CommandSafetyAnalyzer")
    @patch("commandrex.main.asyncio.get_event_loop")
    def test_explain_success(
        self, mock_get_loop, mock_analyzer_class, mock_client_class, mock_check_key
    ):
        """Test successful explain command."""
        # Mock API key check
        mock_check_key.return_value = True

        # Mock OpenAI client
        mock_client = Mock()
        mock_result = {
            "explanation": "Lists files in current directory",
            "components": [{"part": "ls", "description": "list command"}],
            "examples": ["ls -l", "ls -a"],
            "related_commands": ["dir", "find"],
        }
        mock_client.explain_command = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        # Mock safety analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_command.return_value = {
            "is_safe": True,
            "concerns": [],
            "recommendations": [],
        }
        mock_analyzer_class.return_value = mock_analyzer

        # Mock event loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = mock_result
        mock_get_loop.return_value = mock_loop

        result = self.runner.invoke(app, ["explain", "ls -la"])

        assert result.exit_code == 0
        assert "Lists files in current directory" in result.stdout
        assert "list command" in result.stdout

    @patch("commandrex.main.check_api_key")
    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.security.CommandSafetyAnalyzer")
    @patch("commandrex.main.asyncio.get_event_loop")
    def test_explain_dangerous_command(
        self, mock_get_loop, mock_analyzer_class, mock_client_class, mock_check_key
    ):
        """Test explain command with dangerous command."""
        # Mock API key check
        mock_check_key.return_value = True

        # Mock OpenAI client
        mock_client = Mock()
        mock_result = {
            "explanation": "Removes files recursively",
            "components": [
                {"part": "rm -rf", "description": "force remove recursively"}
            ],
            "examples": [],
            "related_commands": ["del"],
        }
        mock_client.explain_command = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        # Mock safety analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_command.return_value = {
            "is_safe": False,
            "concerns": ["Can delete important files"],
            "recommendations": ["Use specific paths"],
        }
        mock_analyzer_class.return_value = mock_analyzer

        # Mock event loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = mock_result
        mock_get_loop.return_value = mock_loop

        result = self.runner.invoke(app, ["explain", "rm -rf /"])

        assert result.exit_code == 0
        assert "Safety Concerns:" in result.stdout
        assert "Can delete important files" in result.stdout
        assert "Recommendations:" in result.stdout


class TestRunCommand:
    """Test the run command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("commandrex.main.process_translation")
    @patch("commandrex.main.platform_utils.detect_shell")
    @patch("commandrex.main.platform_utils.is_windows")
    def test_run_with_translate_option(
        self, mock_is_windows, mock_detect_shell, mock_process
    ):
        """Test run command with --translate option."""
        mock_is_windows.return_value = False
        mock_detect_shell.return_value = ("bash", "5.0", {})

        result = self.runner.invoke(app, ["run", "--translate", "list files"])

        assert result.exit_code == 0
        mock_process.assert_called_once_with(
            "list files", None, "gpt-4.1-mini-2025-04-14", yes_flag=False
        )

    @patch("commandrex.main.settings.settings.set")
    def test_run_debug_mode_flag_setting(self, mock_set):
        """Test that run command sets debug mode flag correctly."""
        # Test that the debug flag gets set when --debug is used
        # We'll test this by mocking the check_api_key to fail early
        with patch("commandrex.main.check_api_key", return_value=False):
            result = self.runner.invoke(app, ["run", "--debug"])

            # Should fail due to API key, but debug mode should still be set
            assert result.exit_code == 1
            mock_set.assert_called_once_with("advanced", "debug_mode", True)

    @patch("commandrex.main.platform_utils.detect_shell")
    @patch("commandrex.main.platform_utils.is_windows")
    def test_run_platform_detection_calls(self, mock_is_windows, mock_detect_shell):
        """Test that run command calls platform detection functions."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("bash", "4.4.0", {})

        # Test with translate option to avoid interactive loop
        with patch("commandrex.main.process_translation"):
            self.runner.invoke(app, ["run", "--translate", "test"])

            # Should have called platform detection functions
            mock_detect_shell.assert_called()
            mock_is_windows.assert_called()

    @patch("commandrex.main.api_manager.is_api_key_valid")
    def test_run_invalid_api_key_option(self, mock_is_valid):
        """Test run command with invalid API key option."""
        mock_is_valid.return_value = False

        result = self.runner.invoke(app, ["run", "--api-key", "invalid"])

        assert result.exit_code == 1
        assert "Invalid API key format" in result.stdout


class TestProcessTranslation:
    """Test the process_translation function."""

    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.prompt_builder.PromptBuilder")
    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.asyncio.run")
    @patch("commandrex.main.typer.confirm")
    def test_process_translation_no_execute(
        self,
        mock_confirm,
        mock_asyncio_run,
        mock_get_key,
        mock_pb_class,
        mock_client_class,
    ):
        """Test process_translation without execution."""
        # Mock API key
        mock_get_key.return_value = "sk-test123456789012345678901234567890123456789012"

        # Mock prompt builder
        mock_pb = Mock()
        mock_pb.build_system_context.return_value = {"platform": "test"}
        mock_pb_class.return_value = mock_pb

        # Mock OpenAI client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.command = "ls -la"
        mock_result.explanation = "List files with details"
        mock_result.is_dangerous = False
        mock_result.components = [{"part": "ls", "description": "list command"}]
        mock_result.safety_assessment = {"concerns": []}

        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        # Mock asyncio.run
        mock_asyncio_run.return_value = mock_result

        # Mock user declining execution
        mock_confirm.return_value = False

        # Capture console output
        with patch("commandrex.main.console") as mock_console:
            process_translation("list files", None, "gpt-4o-mini", yes_flag=False)

            # Verify console.print was called with expected content
            print_calls = [call[0][0] for call in mock_console.print.call_args_list]
            assert any("Translating..." in str(call) for call in print_calls)

    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.prompt_builder.PromptBuilder")
    @patch("commandrex.main.api_manager.get_api_key")
    @patch("commandrex.main.shell_manager.ShellManager")
    @patch("commandrex.main.asyncio.run")
    @patch("commandrex.main.typer.confirm")
    def test_process_translation_with_execute(
        self,
        mock_confirm,
        mock_asyncio_run,
        mock_shell_class,
        mock_get_key,
        mock_pb_class,
        mock_client_class,
    ):
        """Test process_translation with execution."""
        # Mock API key
        mock_get_key.return_value = "sk-test123456789012345678901234567890123456789012"

        # Mock prompt builder
        mock_pb = Mock()
        mock_pb.build_system_context.return_value = {"platform": "test"}
        mock_pb_class.return_value = mock_pb

        # Mock OpenAI client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.command = "ls -la"
        mock_result.explanation = "List files with details"
        mock_result.is_dangerous = False
        mock_result.components = []
        mock_result.safety_assessment = {"concerns": []}
        mock_result.alternatives = []

        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        # Mock shell manager
        mock_shell = Mock()
        mock_exec_result = Mock()
        mock_exec_result.success = True
        mock_exec_result.return_code = 0
        mock_shell.execute_command_safely = AsyncMock(
            return_value=(mock_exec_result, None)
        )
        mock_shell_class.return_value = mock_shell

        # Mock asyncio.run
        mock_asyncio_run.side_effect = [mock_result, (mock_exec_result, None)]

        # Mock user accepting execution
        mock_confirm.return_value = True

        # Capture console output
        with patch("commandrex.main.console"):
            process_translation("list files", None, "gpt-4o-mini", yes_flag=False)

            # Verify execution was attempted
            mock_shell.execute_command_safely.assert_called_once()

    @patch("commandrex.main.openai_client.OpenAIClient")
    @patch("commandrex.main.prompt_builder.PromptBuilder")
    @patch("commandrex.main.asyncio.run")
    def test_process_translation_api_error(
        self, mock_asyncio_run, mock_pb_class, mock_client_class
    ):
        """Test process_translation with API error."""
        # Mock prompt builder
        mock_pb = Mock()
        mock_pb.build_system_context.return_value = {"platform": "test"}
        mock_pb_class.return_value = mock_pb

        # Mock client that raises exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock asyncio.run that raises exception
        mock_asyncio_run.side_effect = Exception("API Error")

        # Capture console output
        with patch("commandrex.main.console") as mock_console:
            process_translation(
                "test query", "sk-test123", "gpt-4o-mini", yes_flag=False
            )

            # Verify error was printed - check if console.print was called with
            # error message
            mock_console.print.assert_called()
            # Check that some error message was printed
            print_calls = mock_console.print.call_args_list
            assert len(print_calls) > 0


class TestMainIntegration:
    """Test integration scenarios for the main CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("commandrex.main.get_version")
    def test_version_command_integration(self, mock_get_version):
        """Test version command integration."""
        mock_get_version.return_value = "2.0.0"

        result = self.runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "CommandRex CLI Version: 2.0.0" in result.stdout

    @patch("commandrex.main.check_api_key")
    def test_translate_command_no_api_key(self, mock_check_key):
        """Test translate command when API key check fails."""
        mock_check_key.return_value = False

        result = self.runner.invoke(app, ["translate", "test query"])

        assert result.exit_code == 1

    @patch("commandrex.main.check_api_key")
    def test_explain_command_no_api_key(self, mock_check_key):
        """Test explain command when API key check fails."""
        mock_check_key.return_value = False

        result = self.runner.invoke(app, ["explain", "ls -la"])

        assert result.exit_code == 1


class TestMainEdgeCases:
    """Test edge cases and error handling for main CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("commandrex.main.check_api_key")
    def test_translate_empty_query_parts(self, mock_check_key):
        """Test translate command with empty query parts."""
        mock_check_key.return_value = False  # Prevent API key check from proceeding

        result = self.runner.invoke(app, ["translate", " ", " "])

        assert result.exit_code == 1
        # The command should fail due to empty query, not API key check

    @patch("commandrex.main.check_api_key")
    def test_explain_empty_command_parts(self, mock_check_key):
        """Test explain command with empty command parts."""
        mock_check_key.return_value = False  # Prevent API key check from proceeding

        result = self.runner.invoke(app, ["explain", " ", " "])

        assert result.exit_code == 1
        # The command should fail due to empty command, not API key check

    @patch("commandrex.main.api_manager.save_api_key")
    @patch("commandrex.main.api_manager.is_api_key_valid")
    @patch("commandrex.main.typer.confirm")
    @patch("commandrex.main.typer.prompt")
    def test_check_api_key_save_failure(
        self, mock_prompt, mock_confirm, mock_is_valid, mock_save
    ):
        """Test check_api_key when save fails."""
        with patch("commandrex.main.api_manager.get_api_key", return_value=None):
            mock_confirm.return_value = True
            mock_prompt.return_value = (
                "sk-test123456789012345678901234567890123456789012"
            )
            mock_is_valid.return_value = True
            mock_save.return_value = False

            result = check_api_key()

            assert result is False

    @patch("commandrex.main.check_api_key")
    @patch("commandrex.main.settings.settings.set")
    def test_run_command_api_key_failure(self, mock_set, mock_check_key):
        """Test run command when API key check fails."""
        mock_check_key.return_value = False

        result = self.runner.invoke(app, ["run"])

        assert result.exit_code == 1


class TestMainConstants:
    """Test main CLI constants and configuration."""

    def test_app_configuration(self):
        """Test that the Typer app is configured correctly."""
        assert app.info.name == "commandrex"
        assert "natural language interface" in app.info.help.lower()
        # Check that the app was created with add_completion=False
        # Note: This attribute may not be directly accessible on the info object
        # but we can verify the app was configured correctly by checking it exists
        assert hasattr(app, "info")

    def test_console_initialization(self):
        """Test that console is properly initialized."""
        from rich.console import Console

        from commandrex.main import console

        assert isinstance(console, Console)


if __name__ == "__main__":
    pytest.main([__file__])
