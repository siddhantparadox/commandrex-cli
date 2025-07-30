"""
Unit tests for the prompt_builder module.

This module tests the PromptBuilder class which handles prompt construction
for OpenAI API calls with platform and shell awareness.
"""

from unittest.mock import patch

import pytest

from commandrex.translator.prompt_builder import PromptBuilder


class TestPromptBuilderInitialization:
    """Test PromptBuilder initialization and basic setup."""

    def test_prompt_builder_initialization(self):
        """Test that PromptBuilder initializes correctly."""
        builder = PromptBuilder()

        assert builder is not None
        assert hasattr(builder, "base_system_prompt")
        assert hasattr(builder, "safety_prompt")
        assert hasattr(builder, "platform_prompts")
        assert hasattr(builder, "shell_prompts")
        assert hasattr(builder, "platform_shell_overrides")

    def test_base_system_prompt_content(self):
        """Test that base system prompt contains expected content."""
        builder = PromptBuilder()

        assert "CommandRex" in builder.base_system_prompt
        assert "JSON format" in builder.base_system_prompt
        assert "command" in builder.base_system_prompt
        assert "explanation" in builder.base_system_prompt
        assert "safety_assessment" in builder.base_system_prompt

    def test_safety_prompt_content(self):
        """Test that safety prompt contains security guidelines."""
        builder = PromptBuilder()

        assert "SAFETY GUIDELINES" in builder.safety_prompt
        assert "Never generate commands that could harm" in builder.safety_prompt
        assert "Flag commands that delete files" in builder.safety_prompt
        assert "Provide clear warnings" in builder.safety_prompt

    def test_platform_prompts_structure(self):
        """Test that platform prompts are properly structured."""
        builder = PromptBuilder()

        expected_platforms = ["windows", "macos", "linux"]
        for platform in expected_platforms:
            assert platform in builder.platform_prompts
            assert isinstance(builder.platform_prompts[platform], str)
            assert len(builder.platform_prompts[platform]) > 0

    def test_shell_prompts_structure(self):
        """Test that shell prompts are properly structured."""
        builder = PromptBuilder()

        expected_shells = ["bash", "zsh", "powershell", "cmd"]
        for shell in expected_shells:
            assert shell in builder.shell_prompts
            assert isinstance(builder.shell_prompts[shell], str)
            assert len(builder.shell_prompts[shell]) > 0

    def test_platform_shell_overrides_structure(self):
        """Test that platform shell overrides are properly structured."""
        builder = PromptBuilder()

        assert "windows" in builder.platform_shell_overrides
        assert "bash" in builder.platform_shell_overrides["windows"]
        assert "Git Bash" in builder.platform_shell_overrides["windows"]["bash"]


class TestPlatformPromptGeneration:
    """Test platform-specific prompt generation."""

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_platform_prompt_windows_git_bash(
        self, mock_detect_shell, mock_is_windows
    ):
        """Test platform prompt for Git Bash on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("bash", "4.4.0", {})

        builder = PromptBuilder()
        prompt = builder._get_platform_prompt()

        assert "Git Bash" in prompt
        assert "Unix-style commands" in prompt
        assert "forward slashes" in prompt
        assert "NOT Windows commands" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_platform_prompt_windows_standard(
        self, mock_detect_shell, mock_is_windows
    ):
        """Test platform prompt for standard Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("powershell", "5.1", {})

        builder = PromptBuilder()
        prompt = builder._get_platform_prompt()

        assert "Windows system" in prompt
        assert "PowerShell commands" in prompt
        assert "backslashes" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_macos")
    def test_get_platform_prompt_macos(self, mock_is_macos, mock_is_windows):
        """Test platform prompt for macOS."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True

        builder = PromptBuilder()
        prompt = builder._get_platform_prompt()

        assert "macOS system" in prompt
        assert "Unix-style commands" in prompt
        assert "Homebrew" in prompt
        assert "forward slashes" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_macos")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_linux")
    def test_get_platform_prompt_linux(
        self, mock_is_linux, mock_is_macos, mock_is_windows
    ):
        """Test platform prompt for Linux."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_is_linux.return_value = True

        builder = PromptBuilder()
        prompt = builder._get_platform_prompt()

        assert "Linux system" in prompt
        assert "Unix commands" in prompt
        assert "package managers" in prompt
        assert "forward slashes" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_macos")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_linux")
    def test_get_platform_prompt_unknown(
        self, mock_is_linux, mock_is_macos, mock_is_windows
    ):
        """Test platform prompt for unknown platform."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_is_linux.return_value = False

        builder = PromptBuilder()
        prompt = builder._get_platform_prompt()

        assert "Unix-like systems" in prompt


class TestShellPromptGeneration:
    """Test shell-specific prompt generation."""

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_shell_prompt_no_shell_detected(self, mock_detect_shell):
        """Test shell prompt when no shell is detected."""
        mock_detect_shell.return_value = None

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "standard shell syntax" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_get_shell_prompt_git_bash_on_windows(
        self, mock_is_windows, mock_detect_shell
    ):
        """Test shell prompt for Git Bash on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = (
            "bash",
            "4.4.0",
            {
                "supports_redirection": True,
                "supports_pipes": True,
                "filename_completion": True,
            },
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "Git Bash" in prompt
        assert "Unix commands" in prompt
        assert "forward slashes" in prompt
        assert "NOT use PowerShell" in prompt
        assert "4.4.0" in prompt
        assert "Shell capabilities" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_shell_prompt_powershell(self, mock_detect_shell):
        """Test shell prompt for PowerShell."""
        mock_detect_shell.return_value = (
            "powershell",
            "5.1",
            {
                "supports_redirection": True,
                "object_pipeline": True,
                "type_system": True,
            },
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "PowerShell" in prompt
        assert "cmdlets" in prompt
        assert "verb-noun format" in prompt
        assert "$variables" in prompt
        assert "object-oriented pipeline" in prompt
        assert "5.1" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_shell_prompt_cmd(self, mock_detect_shell):
        """Test shell prompt for Windows CMD."""
        mock_detect_shell.return_value = (
            "cmd",
            "10.0",
            {"supports_redirection": True, "supports_pipes": False},
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "Command Prompt" in prompt
        assert "%variables%" in prompt
        assert "backslashes" in prompt
        assert "limited scripting" in prompt
        assert "10.0" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_get_shell_prompt_bash_unix(self, mock_is_windows, mock_detect_shell):
        """Test shell prompt for Bash on Unix systems."""
        mock_is_windows.return_value = False
        mock_detect_shell.return_value = (
            "bash",
            "5.0",
            {
                "supports_redirection": True,
                "process_substitution": True,
                "array_support": True,
            },
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "bash" in prompt
        assert "$variables" in prompt
        assert "forward slashes" in prompt
        assert "process substitution" in prompt
        assert "5.0" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_shell_prompt_zsh(self, mock_detect_shell):
        """Test shell prompt for Zsh."""
        mock_detect_shell.return_value = (
            "zsh",
            "5.8",
            {"supports_redirection": True, "array_support": True},
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "zsh" in prompt
        assert "globbing features" in prompt
        assert "enhanced array handling" in prompt
        assert "5.8" in prompt

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_shell_prompt_fish(self, mock_detect_shell):
        """Test shell prompt for Fish shell."""
        mock_detect_shell.return_value = (
            "fish",
            "3.1",
            {"supports_redirection": True, "supports_unicode": True},
        )

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "fish" in prompt
        assert "different scripting syntax" in prompt
        assert "built-in functions" in prompt
        assert "3.1" in prompt


class TestSystemContextBuilding:
    """Test system context building functionality."""

    @patch("commandrex.translator.prompt_builder.platform_utils.get_platform_info")
    @patch("commandrex.translator.prompt_builder.platform_utils.supports_ansi_colors")
    @patch("commandrex.translator.prompt_builder.platform_utils.get_terminal_size")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_system_context_with_platform_info(
        self,
        mock_detect_shell,
        mock_get_terminal_size,
        mock_supports_ansi_colors,
        mock_get_platform_info,
    ):
        """Test building system context with platform information."""
        mock_get_platform_info.return_value = {
            "platform": "Windows",
            "version": "10.0.19041",
            "architecture": "AMD64",
        }
        mock_supports_ansi_colors.return_value = True
        mock_get_terminal_size.return_value = (80, 24)
        mock_detect_shell.return_value = ("powershell", "5.1", {"supports_pipes": True})

        builder = PromptBuilder()
        context = builder.build_system_context(include_platform_info=True)

        assert "platform" in context
        assert "version" in context
        assert "architecture" in context
        assert "supports_ansi_colors" in context
        assert "terminal_size" in context
        assert "shell_name" in context
        assert "shell_version" in context
        assert "shell_capabilities" in context

        assert context["platform"] == "Windows"
        assert context["supports_ansi_colors"] is True
        assert context["terminal_size"] == (80, 24)
        assert context["shell_name"] == "powershell"

    def test_build_system_context_without_platform_info(self):
        """Test building system context without platform information."""
        builder = PromptBuilder()
        context = builder.build_system_context(include_platform_info=False)

        assert context == {}

    @patch("commandrex.translator.prompt_builder.platform_utils.get_platform_info")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_system_context_no_shell_detected(
        self, mock_detect_shell, mock_get_platform_info
    ):
        """Test building system context when no shell is detected."""
        mock_get_platform_info.return_value = {"platform": "Linux"}
        mock_detect_shell.return_value = None

        builder = PromptBuilder()
        context = builder.build_system_context(include_platform_info=True)

        assert "platform" in context
        assert "shell_name" not in context
        assert "shell_version" not in context
        assert "shell_capabilities" not in context


class TestPlatformExamples:
    """Test platform-specific example generation."""

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_platform_examples_git_bash(self, mock_detect_shell, mock_is_windows):
        """Test getting examples for Git Bash on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("bash", "4.4.0", {})

        builder = PromptBuilder()
        examples = builder._get_platform_examples()

        assert "GIT BASH ON WINDOWS" in examples
        assert "ls -la" in examples
        assert "find ~/Downloads" in examples
        assert "ps aux" in examples

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_platform_examples_powershell(self, mock_detect_shell, mock_is_windows):
        """Test getting examples for PowerShell on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("powershell", "5.1", {})

        builder = PromptBuilder()
        examples = builder._get_platform_examples()

        assert "POWERSHELL" in examples
        assert "Get-ChildItem" in examples
        assert "Where-Object" in examples
        assert "Sort-Object" in examples

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_get_platform_examples_cmd(self, mock_detect_shell, mock_is_windows):
        """Test getting examples for Windows CMD."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("cmd", "10.0", {})

        builder = PromptBuilder()
        examples = builder._get_platform_examples()

        assert "WINDOWS CMD" in examples
        assert "dir" in examples
        assert "findstr" in examples
        assert "tasklist" in examples

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_macos")
    def test_get_platform_examples_macos(self, mock_is_macos, mock_is_windows):
        """Test getting examples for macOS."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True

        builder = PromptBuilder()
        examples = builder._get_platform_examples()

        assert "MACOS" in examples
        assert "find ~/Downloads" in examples
        assert "ps aux" in examples
        assert "tar -czf" in examples

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_macos")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_linux")
    def test_get_platform_examples_linux(
        self, mock_is_linux, mock_is_macos, mock_is_windows
    ):
        """Test getting examples for Linux."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_is_linux.return_value = True

        builder = PromptBuilder()
        examples = builder._get_platform_examples()

        assert "LINUX" in examples
        assert "find ~/Downloads" in examples
        assert "ps aux" in examples
        assert "uptime" in examples


class TestShellSpecificExamples:
    """Test shell-specific example generation."""

    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_get_shell_specific_examples_git_bash(self, mock_is_windows):
        """Test getting shell-specific examples for Git Bash."""
        mock_is_windows.return_value = True

        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("bash")

        assert "ls -la" in examples
        assert "grep -r" in examples
        assert "ps aux" in examples
        assert "mkdir -p" in examples

    def test_get_shell_specific_examples_powershell(self):
        """Test getting shell-specific examples for PowerShell."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("powershell")

        assert "Get-ChildItem" in examples
        assert "Select-String" in examples
        assert "Get-Process" in examples
        assert "New-Item" in examples

    def test_get_shell_specific_examples_cmd(self):
        """Test getting shell-specific examples for CMD."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("cmd")

        assert "dir /a" in examples
        assert "findstr" in examples
        assert "tasklist" in examples
        assert "mkdir" in examples

    def test_get_shell_specific_examples_bash_unix(self):
        """Test getting shell-specific examples for Bash on Unix."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("bash")

        assert "ls -la" in examples
        assert "grep -r" in examples
        assert "ps aux" in examples
        assert "mkdir -p" in examples

    def test_get_shell_specific_examples_zsh(self):
        """Test getting shell-specific examples for Zsh."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("zsh")

        assert "ls -la" in examples
        assert "grep -r" in examples
        assert "cp *.txt" in examples

    def test_get_shell_specific_examples_fish(self):
        """Test getting shell-specific examples for Fish."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("fish")

        assert "ls -la" in examples
        assert "for file in" in examples
        assert "end" in examples

    def test_get_shell_specific_examples_unknown_shell(self):
        """Test getting shell-specific examples for unknown shell."""
        builder = PromptBuilder()
        examples = builder._get_shell_specific_examples("unknown_shell")

        assert "ls -la" in examples
        assert "grep -r" in examples
        assert "find . -name" in examples


class TestTranslationPromptBuilding:
    """Test translation prompt building functionality."""

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_build_translation_prompt_basic(self, mock_is_windows, mock_detect_shell):
        """Test building a basic translation prompt."""
        mock_is_windows.return_value = False
        mock_detect_shell.return_value = ("bash", "5.0", {"supports_pipes": True})

        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files in current directory")

        assert len(messages) >= 3  # System, context, user message
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "list files in current directory"

        # Check that system prompt contains expected content
        system_content = messages[0]["content"]
        assert "CommandRex" in system_content
        assert "SAFETY GUIDELINES" in system_content

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_build_translation_prompt_git_bash_special_case(
        self, mock_is_windows, mock_detect_shell
    ):
        """Test building translation prompt for Git Bash on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("bash", "4.4.0", {"supports_pipes": True})

        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files")

        system_content = messages[0]["content"]
        assert "CRITICAL: You are in Git Bash on Windows" in system_content
        assert "Unix/Bash commands like 'ls'" in system_content
        assert "NOT Windows commands like 'Get-ChildItem'" in system_content

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_translation_prompt_with_command_history(self, mock_detect_shell):
        """Test building translation prompt with command history."""
        mock_detect_shell.return_value = ("bash", "5.0", {})

        builder = PromptBuilder()
        history = ["ls -la", "cd Documents", "grep -r 'test' .", "pwd", "cat file.txt"]
        messages = builder.build_translation_prompt(
            "find large files", command_history=history
        )

        # Find the history message
        history_message = None
        for msg in messages:
            if "Recent command history" in msg.get("content", ""):
                history_message = msg
                break

        assert history_message is not None
        assert history_message["role"] == "system"
        # Should only include last 5 commands
        for cmd in history:
            assert cmd in history_message["content"]

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_translation_prompt_with_user_preferences(self, mock_detect_shell):
        """Test building translation prompt with user preferences."""
        mock_detect_shell.return_value = ("bash", "5.0", {})

        builder = PromptBuilder()
        preferences = {
            "verbose_output": True,
            "preferred_editor": "vim",
            "color_output": False,
        }
        messages = builder.build_translation_prompt(
            "edit a file", user_preferences=preferences
        )

        # Find the preferences message
        pref_message = None
        for msg in messages:
            if "User preferences" in msg.get("content", ""):
                pref_message = msg
                break

        assert pref_message is not None
        assert pref_message["role"] == "system"
        assert "verbose_output: True" in pref_message["content"]
        assert "preferred_editor: vim" in pref_message["content"]
        assert "color_output: False" in pref_message["content"]

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_translation_prompt_with_shell_examples(self, mock_detect_shell):
        """Test that translation prompt includes shell-specific examples."""
        mock_detect_shell.return_value = (
            "powershell",
            "5.1",
            {"object_pipeline": True},
        )

        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list processes")

        # Find the shell examples message
        examples_message = None
        for msg in messages:
            if "Examples for powershell shell" in msg.get("content", ""):
                examples_message = msg
                break

        assert examples_message is not None
        assert examples_message["role"] == "system"
        assert "Get-ChildItem" in examples_message["content"]

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_build_translation_prompt_no_shell_detected(self, mock_detect_shell):
        """Test building translation prompt when no shell is detected."""
        mock_detect_shell.return_value = None

        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files")

        # Should still work, just without shell-specific examples
        assert len(messages) >= 3
        assert messages[-1]["content"] == "list files"


class TestExplanationPromptBuilding:
    """Test explanation prompt building functionality."""

    def test_build_explanation_prompt_basic(self):
        """Test building a basic explanation prompt."""
        builder = PromptBuilder()
        messages = builder.build_explanation_prompt("ls -la")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Explain this command: ls -la"

        system_content = messages[0]["content"]
        assert "CommandRex" in system_content
        assert "explaining terminal commands" in system_content
        assert "JSON format" in system_content
        assert "explanation" in system_content
        assert "components" in system_content

    def test_build_explanation_prompt_complex_command(self):
        """Test building explanation prompt for complex command."""
        complex_command = "find . -name '*.txt' -type f -size +1M -exec rm {} \\;"

        builder = PromptBuilder()
        messages = builder.build_explanation_prompt(complex_command)

        assert len(messages) == 2
        assert complex_command in messages[1]["content"]

        system_content = messages[0]["content"]
        assert "Break down each component" in system_content
        assert "potential pitfalls" in system_content
        assert "related commands" in system_content


class TestSafetyAssessmentPromptBuilding:
    """Test safety assessment prompt building functionality."""

    def test_build_safety_assessment_prompt_basic(self):
        """Test building a basic safety assessment prompt."""
        builder = PromptBuilder()
        messages = builder.build_safety_assessment_prompt("ls -la")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Assess the safety of this command: ls -la"

        system_content = messages[0]["content"]
        assert "CommandRex" in system_content
        assert "command safety" in system_content
        assert "JSON format" in system_content
        assert "is_safe" in system_content
        assert "risk_level" in system_content

    def test_build_safety_assessment_prompt_dangerous_command(self):
        """Test building safety assessment prompt for dangerous command."""
        dangerous_command = "rm -rf /"

        builder = PromptBuilder()
        messages = builder.build_safety_assessment_prompt(dangerous_command)

        assert len(messages) == 2
        assert dangerous_command in messages[1]["content"]

        system_content = messages[0]["content"]
        assert "destructive operations" in system_content
        assert "Data loss" in system_content
        assert "Security risks" in system_content
        assert "safer_alternatives" in system_content


class TestPromptBuilderIntegration:
    """Test integration scenarios for PromptBuilder."""

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    @patch("commandrex.translator.prompt_builder.platform_utils.get_platform_info")
    @patch("commandrex.translator.prompt_builder.platform_utils.is_windows")
    def test_full_prompt_building_workflow(
        self, mock_is_windows, mock_get_platform_info, mock_detect_shell
    ):
        """Test a complete prompt building workflow."""
        mock_is_windows.return_value = True
        mock_get_platform_info.return_value = {"platform": "Windows", "version": "10"}
        mock_detect_shell.return_value = (
            "powershell",
            "5.1",
            {"object_pipeline": True},
        )

        builder = PromptBuilder()

        # Test translation prompt
        translation_messages = builder.build_translation_prompt(
            "find large files",
            command_history=["ls", "cd Documents"],
            user_preferences={"verbose": True},
        )

        assert (
            len(translation_messages) >= 5
        )  # System, context, examples, history, preferences, user

        # Test explanation prompt
        explanation_messages = builder.build_explanation_prompt(
            "Get-ChildItem -Recurse"
        )
        assert len(explanation_messages) == 2

        # Test safety assessment prompt
        safety_messages = builder.build_safety_assessment_prompt("Remove-Item -Recurse")
        assert len(safety_messages) == 2

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_cross_platform_compatibility(self, mock_detect_shell):
        """Test that PromptBuilder works across different platforms."""
        # Test with different shell configurations
        test_shells = [
            ("bash", "5.0", {"supports_pipes": True}),
            ("powershell", "5.1", {"object_pipeline": True}),
            ("cmd", "10.0", {"supports_redirection": True}),
            ("zsh", "5.8", {"array_support": True}),
            ("fish", "3.1", {"supports_unicode": True}),
        ]

        builder = PromptBuilder()

        for shell_name, version, capabilities in test_shells:
            mock_detect_shell.return_value = (shell_name, version, capabilities)

            # Test that all prompt types can be built
            translation_messages = builder.build_translation_prompt("list files")
            explanation_messages = builder.build_explanation_prompt("ls -la")
            safety_messages = builder.build_safety_assessment_prompt("rm file.txt")

            assert len(translation_messages) >= 3
            assert len(explanation_messages) == 2
            assert len(safety_messages) == 2

            # Test that shell-specific content is included
            system_content = translation_messages[0]["content"]
            assert shell_name in system_content or "shell" in system_content


class TestPromptBuilderEdgeCases:
    """Test edge cases and error handling for PromptBuilder."""

    def test_empty_user_request(self):
        """Test handling of empty user request."""
        builder = PromptBuilder()
        messages = builder.build_translation_prompt("")

        assert len(messages) >= 3
        assert messages[-1]["content"] == ""

    def test_none_command_history(self):
        """Test handling of None command history."""
        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files", command_history=None)

        # Should not include history message
        history_found = any(
            "Recent command history" in msg.get("content", "") for msg in messages
        )
        assert not history_found

    def test_empty_command_history(self):
        """Test handling of empty command history."""
        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files", command_history=[])

        # Should not include history message
        history_found = any(
            "Recent command history" in msg.get("content", "") for msg in messages
        )
        assert not history_found

    def test_none_user_preferences(self):
        """Test handling of None user preferences."""
        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files", user_preferences=None)

        # Should not include preferences message
        pref_found = any(
            "User preferences" in msg.get("content", "") for msg in messages
        )
        assert not pref_found

    def test_empty_user_preferences(self):
        """Test handling of empty user preferences."""
        builder = PromptBuilder()
        messages = builder.build_translation_prompt("list files", user_preferences={})

        # Should not include preferences message
        pref_found = any(
            "User preferences" in msg.get("content", "") for msg in messages
        )
        assert not pref_found

    def test_very_long_command_history(self):
        """Test handling of very long command history."""
        builder = PromptBuilder()
        long_history = [f"command_{i}" for i in range(20)]  # 20 commands
        messages = builder.build_translation_prompt(
            "list files", command_history=long_history
        )

        # Find the history message
        history_message = None
        for msg in messages:
            if "Recent command history" in msg.get("content", ""):
                history_message = msg
                break

        assert history_message is not None
        # Should only include last 5 commands
        content = history_message["content"]
        assert "command_19" in content  # Last command
        assert "command_15" in content  # 5th from last
        assert "command_14" not in content  # 6th from last should not be included

    @patch("commandrex.translator.prompt_builder.platform_utils.detect_shell")
    def test_malformed_shell_info(self, mock_detect_shell):
        """Test handling of malformed shell information."""
        # Test with incomplete shell info
        mock_detect_shell.return_value = ("bash", None, {})

        builder = PromptBuilder()
        prompt = builder._get_shell_prompt()

        assert "bash" in prompt
        assert "None" in prompt  # Should handle None version gracefully

    def test_special_characters_in_commands(self):
        """Test handling of special characters in commands."""
        builder = PromptBuilder()
        special_command = "grep -r 'test\"with\"quotes' . | awk '{print $1}'"

        messages = builder.build_explanation_prompt(special_command)
        assert len(messages) == 2
        assert special_command in messages[1]["content"]

        safety_messages = builder.build_safety_assessment_prompt(special_command)
        assert len(messages) == 2
        assert special_command in safety_messages[1]["content"]


class TestPromptBuilderConstants:
    """Test PromptBuilder constants and static content."""

    def test_platform_prompts_completeness(self):
        """Test that all expected platforms have prompts."""
        builder = PromptBuilder()

        required_platforms = ["windows", "macos", "linux"]
        for platform in required_platforms:
            assert platform in builder.platform_prompts
            prompt = builder.platform_prompts[platform]
            assert len(prompt) > 50  # Should be substantial
            assert (
                platform.title() in prompt
                or platform.upper() in prompt
                or "macOS" in prompt
            )

    def test_shell_prompts_completeness(self):
        """Test that all expected shells have prompts."""
        builder = PromptBuilder()

        required_shells = ["bash", "zsh", "powershell", "cmd"]
        for shell in required_shells:
            assert shell in builder.shell_prompts
            prompt = builder.shell_prompts[shell]
            assert len(prompt) > 10  # Should be substantial
            assert (
                shell.title() in prompt
                or shell.upper() in prompt
                or shell in prompt
                or "PowerShell" in prompt
            )

    def test_safety_prompt_content_quality(self):
        """Test that safety prompt contains comprehensive guidelines."""
        builder = PromptBuilder()
        safety_content = builder.safety_prompt

        safety_keywords = [
            "SAFETY",
            "Never generate commands",
            "harm",
            "delete files",
            "warnings",
            "dangerous",
            "safer alternatives",
            "explain",
        ]

        for keyword in safety_keywords:
            assert keyword.lower() in safety_content.lower()

    def test_base_system_prompt_json_format(self):
        """Test that base system prompt specifies correct JSON format."""
        builder = PromptBuilder()
        base_prompt = builder.base_system_prompt

        json_fields = [
            "command",
            "explanation",
            "safety_assessment",
            "is_safe",
            "concerns",
            "risk_level",
            "components",
            "is_dangerous",
            "alternatives",
        ]

        for field in json_fields:
            assert field in base_prompt


if __name__ == "__main__":
    pytest.main([__file__])
