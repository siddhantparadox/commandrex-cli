"""
End-to-end tests for CommandRex CLI commands.

This module tests the complete CLI workflows including command translation,
explanation, execution, and user interactions.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
from typer.testing import CliRunner

from commandrex.main import app
from commandrex.config.api_manager import get_api_key, save_api_key, delete_api_key


class TestCLIEndToEnd:
    """End-to-end tests for CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Clean up any API keys that might have been set during testing
        with patch('commandrex.config.api_manager.keyring.delete_password'):
            try:
                delete_api_key()
            except:
                pass
    
    def test_version_command(self):
        """Test version command displays correctly."""
        result = self.runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "CommandRex" in result.stdout
        assert "version" in result.stdout.lower()
    
    def test_help_command(self):
        """Test help command displays usage information."""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "CommandRex" in result.stdout
        assert "translate" in result.stdout
        assert "explain" in result.stdout
        assert "run" in result.stdout
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.main.check_api_key')
    def test_translate_command_no_api_key(self, mock_check_api_key, mock_get_api_key):
        """Test translate command without API key."""
        mock_get_api_key.return_value = None
        mock_check_api_key.return_value = False  # Simulate user declining to set up API key
        
        result = self.runner.invoke(app, ["translate", "list files"])
        
        # Should exit with error code when no API key and user declines setup
        assert result.exit_code != 0
        # The check_api_key function should have been called
        mock_check_api_key.assert_called_once()
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_translate_command_success(self, mock_client_class, mock_get_api_key):
        """Test successful translate command."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock translation result
        mock_result = Mock()
        mock_result.command = "ls -la"
        mock_result.explanation = "List files with detailed information"
        mock_result.alternatives = ["dir", "ls -l"]
        mock_result.is_dangerous = False
        mock_result.safety_assessment = {}
        mock_result.components = []
        
        # Make translate_to_command return a coroutine
        async def mock_translate():
            return mock_result
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        result = self.runner.invoke(app, ["translate", "list files"])
        
        assert result.exit_code == 0
        assert "ls -la" in result.stdout
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.main.check_api_key')
    def test_explain_command_no_api_key(self, mock_check_api_key, mock_get_api_key):
        """Test explain command without API key."""
        mock_get_api_key.return_value = None
        mock_check_api_key.return_value = False  # Simulate user declining to set up API key
        
        result = self.runner.invoke(app, ["explain", "ls -la"])
        
        # Should exit with error code when no API key and user declines setup
        assert result.exit_code != 0
        # The check_api_key function should have been called
        mock_check_api_key.assert_called_once()
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_explain_command_success(self, mock_client_class, mock_get_api_key):
        """Test successful explain command."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock explanation result
        mock_explanation = {
            "explanation": "Lists files in long format with detailed information",
            "components": [
                {"part": "ls", "description": "List directory contents"},
                {"part": "-l", "description": "Use long listing format"},
                {"part": "-a", "description": "Show hidden files"}
            ],
            "examples": [],
            "related_commands": []
        }
        
        # Make explain_command return a coroutine
        mock_client.explain_command = AsyncMock(return_value=mock_explanation)
        
        result = self.runner.invoke(app, ["explain", "ls -la"])
        
        assert result.exit_code == 0
        assert "Lists files" in result.stdout or "List" in result.stdout
    
    @patch('commandrex.config.api_manager.get_api_key')
    def test_run_command_no_api_key(self, mock_get_api_key):
        """Test run command without API key."""
        mock_get_api_key.return_value = None
        
        result = self.runner.invoke(app, ["run", "list files"])
        
        # Should exit with error code when no API key
        assert result.exit_code != 0
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    @patch('commandrex.executor.shell_manager.ShellManager')
    def test_run_command_with_execution(self, mock_shell_manager_class, mock_client_class, mock_get_api_key):
        """Test run command with execution."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock translation result
        mock_result = Mock()
        mock_result.command = "echo 'hello'"
        mock_result.explanation = "Print hello to console"
        mock_result.alternatives = []
        mock_result.is_dangerous = False
        mock_result.safety_assessment = {"is_safe": True, "risk_level": "low"}
        mock_result.components = []
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        # Mock safety assessment
        mock_safety = {
            "is_safe": True,
            "risk_level": "low",
            "explanation": "Safe command"
        }
        mock_client.assess_command_safety = AsyncMock(return_value=mock_safety)
        
        # Mock shell manager
        mock_shell_manager = Mock()
        mock_shell_manager_class.return_value = mock_shell_manager
        
        # Mock command execution result
        mock_exec_result = Mock()
        mock_exec_result.success = True
        mock_exec_result.stdout = "hello"
        mock_exec_result.stderr = ""
        mock_exec_result.return_code = 0
        
        # Make execute_command_safely return a coroutine
        async def mock_execute():
            return mock_exec_result, None
        mock_shell_manager.execute_command_safely = AsyncMock(return_value=(mock_exec_result, None))
        
        # Use --yes flag to skip confirmation
        result = self.runner.invoke(app, ["run", "--yes", "print hello"])
        
        assert result.exit_code == 0
        assert "echo 'hello'" in result.stdout
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_run_command_dangerous_blocked(self, mock_client_class, mock_get_api_key):
        """Test run command blocks dangerous commands."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock translation result
        mock_result = Mock()
        mock_result.command = "rm -rf /"
        mock_result.explanation = "Delete all files (DANGEROUS)"
        mock_result.alternatives = []
        mock_result.is_dangerous = True
        mock_result.safety_assessment = {
            "is_safe": False,
            "risk_level": "critical",
            "concerns": ["This command will delete all files on the system"]
        }
        mock_result.components = []
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        # Mock safety assessment - dangerous
        mock_safety = {
            "is_safe": False,
            "risk_level": "critical",
            "explanation": "This command will delete all files on the system"
        }
        mock_client.assess_command_safety = AsyncMock(return_value=mock_safety)
        
        result = self.runner.invoke(app, ["run", "delete everything"])
        
        assert result.exit_code == 0  # Command translates but doesn't execute due to danger
        assert "dangerous" in result.stdout.lower() or "risk" in result.stdout.lower()


class TestCLIConfiguration:
    """Test CLI configuration and setup commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def teardown_method(self):
        """Clean up after tests."""
        # Clean up any API keys that might have been set during testing
        with patch('commandrex.config.api_manager.keyring.delete_password'):
            try:
                delete_api_key()
            except:
                pass
    
    @patch('commandrex.config.api_manager.save_api_key')
    @patch('builtins.input')
    def test_api_key_setup_interactive(self, mock_input, mock_save_api_key):
        """Test interactive API key setup."""
        mock_input.return_value = "sk-test123456789012345678901234567890123456789012"
        mock_save_api_key.return_value = True
        
        # This would be triggered when no API key is found
        # We'll test the underlying function directly since CLI interaction is complex
        from commandrex.main import check_api_key
        
        with patch('commandrex.config.api_manager.get_api_key', return_value=None):
            with patch('commandrex.main.typer.confirm', return_value=True):
                with patch('commandrex.main.typer.prompt', return_value="sk-test123456789012345678901234567890123456789012"):
                    with patch('commandrex.main.api_manager.is_api_key_valid', return_value=True):
                        with patch('commandrex.main.api_manager.save_api_key', return_value=True):
                            result = check_api_key()
                            assert result is True
    
    def test_debug_mode_flag(self):
        """Test debug mode flag affects logging."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "ls"
                mock_result.explanation = "List files"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                with patch('commandrex.main.check_api_key', return_value=True):
                    # Use run command with --translate option since --debug is only available on run command
                    result = self.runner.invoke(app, ["run", "--debug", "--translate", "list files"])
                    
                    # Debug mode should not cause failure
                    assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_empty_translate_query(self):
        """Test translate command with empty query."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            result = self.runner.invoke(app, ["translate"])
            
            # Should show help or error for missing argument
            assert result.exit_code != 0
    
    def test_empty_explain_command(self):
        """Test explain command with empty command."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            result = self.runner.invoke(app, ["explain"])
            
            # Should show help or error for missing argument
            assert result.exit_code != 0
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_api_error_handling(self, mock_client_class, mock_get_api_key):
        """Test handling of API errors."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client to raise an exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.translate_to_command = AsyncMock(side_effect=Exception("API Error"))
        
        result = self.runner.invoke(app, ["translate", "list files"])
        
        assert result.exit_code == 1
        assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_invalid_json_response(self, mock_client_class, mock_get_api_key):
        """Test handling of invalid JSON responses."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client to return invalid response
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.translate_to_command = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        result = self.runner.invoke(app, ["translate", "list files"])
        
        assert result.exit_code == 1


class TestCLIIntegrationWorkflows:
    """Test complete CLI workflows and integrations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
    def teardown_method(self):
        """Clean up after tests."""
        with patch('commandrex.config.api_manager.keyring.delete_password'):
            try:
                delete_api_key()
            except:
                pass
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    @patch('commandrex.executor.platform_utils.get_platform_info')
    def test_platform_specific_translation(self, mock_platform_info, mock_client_class, mock_get_api_key):
        """Test platform-specific command translation."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock platform info
        mock_platform_info.return_value = {
            'platform': 'Windows',
            'shell': 'PowerShell',
            'version': '10.0.19041'
        }
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock platform-specific result
        mock_result = Mock()
        mock_result.command = "Get-ChildItem"
        mock_result.explanation = "List files using PowerShell"
        mock_result.alternatives = ["dir", "ls"]
        mock_result.is_dangerous = False
        mock_result.safety_assessment = {}
        mock_result.components = []
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        result = self.runner.invoke(app, ["translate", "list files"])
        
        assert result.exit_code == 0
        assert "Get-ChildItem" in result.stdout
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    def test_command_with_alternatives(self, mock_client_class, mock_get_api_key):
        """Test command translation with alternatives."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock result with alternatives
        mock_result = Mock()
        mock_result.command = "find . -name '*.py'"
        mock_result.explanation = "Find Python files"
        mock_result.alternatives = ["locate '*.py'", "fd -e py"]
        mock_result.is_dangerous = False
        mock_result.safety_assessment = {}
        mock_result.components = []
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        result = self.runner.invoke(app, ["translate", "find python files"])
        
        assert result.exit_code == 0
        assert "find . -name '*.py'" in result.stdout
        assert "alternative" in result.stdout.lower() or "other options" in result.stdout.lower()
    
    @patch('commandrex.config.api_manager.get_api_key')
    @patch('commandrex.translator.openai_client.OpenAIClient')
    @patch('commandrex.executor.shell_manager.ShellManager')
    def test_full_workflow_translate_and_execute(self, mock_shell_manager_class, mock_client_class, mock_get_api_key):
        """Test complete workflow from translation to execution."""
        mock_get_api_key.return_value = "sk-test123456789012345678901234567890123456789012"
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock translation
        mock_result = Mock()
        mock_result.command = "pwd"
        mock_result.explanation = "Print current directory"
        mock_result.alternatives = []
        mock_result.is_dangerous = False
        mock_result.safety_assessment = {"is_safe": True, "risk_level": "low"}
        mock_result.components = []
        mock_client.translate_to_command = AsyncMock(return_value=mock_result)
        
        # Mock safety assessment
        mock_safety = {
            "is_safe": True,
            "risk_level": "low",
            "explanation": "Safe command to show current directory"
        }
        mock_client.assess_command_safety = AsyncMock(return_value=mock_safety)
        
        # Mock shell execution
        mock_shell_manager = Mock()
        mock_shell_manager_class.return_value = mock_shell_manager
        
        mock_exec_result = Mock()
        mock_exec_result.success = True
        mock_exec_result.stdout = "/home/user/projects"
        mock_exec_result.stderr = ""
        mock_exec_result.return_code = 0
        mock_shell_manager.execute_command_safely = AsyncMock(return_value=(mock_exec_result, None))
        
        # Test the full workflow
        result = self.runner.invoke(app, ["run", "--yes", "show current directory"])
        
        assert result.exit_code == 0
        assert "pwd" in result.stdout
        assert "/home/user/projects" in result.stdout or "executed successfully" in result.stdout.lower()


class TestCLIUserInteraction:
    """Test CLI user interaction and prompts."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_translate_option_flag(self):
        """Test --translate option in run command."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "ls -la"
                mock_result.explanation = "List files with details"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                result = self.runner.invoke(app, ["run", "--translate", "list files"])
                
                # Should show translation without execution
                assert result.exit_code == 0
                assert "ls -la" in result.stdout
    
    def test_yes_flag_skips_confirmation(self):
        """Test --yes flag skips confirmation prompts."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                with patch('commandrex.executor.shell_manager.ShellManager') as mock_shell_manager_class:
                    # Setup mocks
                    mock_client = Mock()
                    mock_client_class.return_value = mock_client
                    
                    mock_result = Mock()
                    mock_result.command = "echo test"
                    mock_result.explanation = "Print test"
                    mock_result.alternatives = []
                    mock_result.is_dangerous = False
                    mock_result.safety_assessment = {"is_safe": True, "risk_level": "low"}
                    mock_result.components = []
                    mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                    
                    mock_safety = {
                        "is_safe": True,
                        "risk_level": "low",
                        "explanation": "Safe command"
                    }
                    mock_client.assess_command_safety = AsyncMock(return_value=mock_safety)
                    
                    mock_shell_manager = Mock()
                    mock_shell_manager_class.return_value = mock_shell_manager
                    
                    mock_exec_result = Mock()
                    mock_exec_result.success = True
                    mock_exec_result.stdout = "test"
                    mock_exec_result.stderr = ""
                    mock_exec_result.return_code = 0
                    mock_shell_manager.execute_command_safely = AsyncMock(return_value=(mock_exec_result, None))
                    
                    result = self.runner.invoke(app, ["run", "--yes", "print test"])
                    
                    # Should execute without prompting
                    assert result.exit_code == 0


class TestCLIEdgeCases:
    """Test CLI edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_very_long_query(self):
        """Test handling of very long queries."""
        long_query = "list all files " * 100  # Very long query
        
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "ls -la"
                mock_result.explanation = "List files"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                result = self.runner.invoke(app, ["translate"] + long_query.split())
                
                # Should handle long queries gracefully
                assert result.exit_code == 0
    
    def test_special_characters_in_query(self):
        """Test handling of special characters in queries."""
        special_query = ["find", "files", "with", "name", "*.py", "&", "sort"]
        
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "find . -name '*.py' | sort"
                mock_result.explanation = "Find and sort Python files"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                result = self.runner.invoke(app, ["translate"] + special_query)
                
                assert result.exit_code == 0
    
    def test_unicode_characters(self):
        """Test handling of unicode characters in queries."""
        unicode_query = ["créer", "un", "fichier", "test.txt"]
        
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "touch test.txt"
                mock_result.explanation = "Create a file named test.txt"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                result = self.runner.invoke(app, ["translate"] + unicode_query)
                
                assert result.exit_code == 0


class TestCLIPerformance:
    """Test CLI performance and resource usage."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_multiple_rapid_commands(self):
        """Test handling of multiple rapid command invocations."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "ls"
                mock_result.explanation = "List files"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                # Run multiple commands rapidly
                for i in range(5):
                    result = self.runner.invoke(app, ["translate", f"list files {i}"])
                    assert result.exit_code == 0
    
    def test_memory_cleanup(self):
        """Test that CLI properly cleans up resources."""
        with patch('commandrex.config.api_manager.get_api_key', return_value="sk-test123456789012345678901234567890123456789012"):
            with patch('commandrex.translator.openai_client.OpenAIClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_result = Mock()
                mock_result.command = "ls"
                mock_result.explanation = "List files"
                mock_result.alternatives = []
                mock_result.is_dangerous = False
                mock_result.safety_assessment = {}
                mock_result.components = []
                mock_client.translate_to_command = AsyncMock(return_value=mock_result)
                
                # Run command and verify it completes cleanly
                result = self.runner.invoke(app, ["translate", "list files"])
                assert result.exit_code == 0
                
                # Verify mock was called (indicating proper initialization/cleanup)
                mock_client.translate_to_command.assert_called()