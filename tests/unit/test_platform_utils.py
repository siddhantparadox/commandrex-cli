"""
Unit tests for commandrex.executor.platform_utils module.

Tests platform detection, shell identification, and cross-platform utilities.
"""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from commandrex.executor.platform_utils import (
    adapt_command_for_shell,
    detect_shell,
    detect_shell_from_behavior,
    detect_shell_from_commands,
    detect_shell_from_environment,
    determine_best_guess_shell,
    find_executable,
    get_command_prefix,
    get_parent_process_info,
    get_platform_info,
    get_shell_capabilities,
    get_shell_startup_command,
    get_shell_version,
    get_terminal_size,
    is_linux,
    is_macos,
    is_windows,
    normalize_path,
    parse_shell_version,
    supports_ansi_colors,
)


class TestPlatformDetection:
    """Test cases for platform detection functions."""

    @patch("platform.system")
    def test_is_windows_true(self, mock_system):
        """Test Windows detection returns True."""
        mock_system.return_value = "Windows"
        assert is_windows() is True

    @patch("platform.system")
    def test_is_windows_false(self, mock_system):
        """Test Windows detection returns False for non-Windows."""
        mock_system.return_value = "Linux"
        assert is_windows() is False

    @patch("platform.system")
    def test_is_macos_true(self, mock_system):
        """Test macOS detection returns True."""
        mock_system.return_value = "Darwin"
        assert is_macos() is True

    @patch("platform.system")
    def test_is_macos_false(self, mock_system):
        """Test macOS detection returns False for non-macOS."""
        mock_system.return_value = "Linux"
        assert is_macos() is False

    @patch("platform.system")
    def test_is_linux_true(self, mock_system):
        """Test Linux detection returns True."""
        mock_system.return_value = "Linux"
        assert is_linux() is True

    @patch("platform.system")
    def test_is_linux_false(self, mock_system):
        """Test Linux detection returns False for non-Linux."""
        mock_system.return_value = "Windows"
        assert is_linux() is False

    @patch("platform.system")
    def test_platform_detection_case_insensitive(self, mock_system):
        """Test platform detection is case insensitive."""
        mock_system.return_value = "WINDOWS"
        assert is_windows() is True

        mock_system.return_value = "darwin"
        assert is_macos() is True

        mock_system.return_value = "LINUX"
        assert is_linux() is True


class TestPlatformInfo:
    """Test cases for get_platform_info function."""

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.python_version")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_platform_info_complete(
        self, mock_detect_shell, mock_python_version, mock_machine, mock_system
    ):
        """Test getting complete platform information."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        mock_python_version.return_value = "3.9.7"
        mock_detect_shell.return_value = ("bash", "5.1.8", {})

        info = get_platform_info()

        assert info["os_name"] == "Linux"
        assert info["architecture"] == "x86_64"
        assert info["python_version"] == "3.9.7"
        assert info["shell_name"] == "bash"
        assert info["shell_version"] == "5.1.8"

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.python_version")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_platform_info_no_shell(
        self, mock_detect_shell, mock_python_version, mock_machine, mock_system
    ):
        """Test platform info when shell detection fails."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"
        mock_python_version.return_value = "3.9.7"
        mock_detect_shell.return_value = None

        info = get_platform_info()

        assert info["os_name"] == "Windows"
        assert info["architecture"] == "AMD64"
        assert info["python_version"] == "3.9.7"
        assert "shell_name" not in info
        assert "shell_version" not in info


class TestShellDetection:
    """Test cases for shell detection functions."""

    @patch("commandrex.executor.platform_utils.detect_shell_from_environment")
    @patch("commandrex.executor.platform_utils.get_shell_capabilities")
    def test_detect_shell_from_environment_success(
        self, mock_capabilities, mock_env_detect
    ):
        """Test successful shell detection from environment."""
        mock_env_detect.return_value = ("bash", "5.1.8")
        mock_capabilities.return_value = {"supports_colors": True}

        result = detect_shell()

        assert result is not None
        assert result[0] == "bash"
        assert result[1] == "5.1.8"
        assert result[2]["supports_colors"] is True

    @patch("commandrex.executor.platform_utils.detect_shell_from_environment")
    @patch("commandrex.executor.platform_utils.detect_shell_from_commands")
    @patch("commandrex.executor.platform_utils.get_shell_capabilities")
    def test_detect_shell_fallback_to_commands(
        self, mock_capabilities, mock_cmd_detect, mock_env_detect
    ):
        """Test shell detection fallback to commands."""
        mock_env_detect.return_value = None
        mock_cmd_detect.return_value = ("zsh", "5.8")
        mock_capabilities.return_value = {"supports_colors": True}

        result = detect_shell()

        assert result is not None
        assert result[0] == "zsh"
        assert result[1] == "5.8"

    @patch("commandrex.executor.platform_utils.detect_shell_from_environment")
    @patch("commandrex.executor.platform_utils.detect_shell_from_commands")
    @patch("commandrex.executor.platform_utils.detect_shell_from_behavior")
    @patch("commandrex.executor.platform_utils.get_shell_capabilities")
    def test_detect_shell_fallback_to_behavior(
        self, mock_capabilities, mock_behavior_detect, mock_cmd_detect, mock_env_detect
    ):
        """Test shell detection fallback to behavior testing."""
        mock_env_detect.return_value = None
        mock_cmd_detect.return_value = None
        mock_behavior_detect.return_value = ("fish", "3.1.2")
        mock_capabilities.return_value = {"supports_colors": True}

        result = detect_shell()

        assert result is not None
        assert result[0] == "fish"
        assert result[1] == "3.1.2"

    @patch("commandrex.executor.platform_utils.detect_shell_from_environment")
    @patch("commandrex.executor.platform_utils.detect_shell_from_commands")
    @patch("commandrex.executor.platform_utils.detect_shell_from_behavior")
    @patch("commandrex.executor.platform_utils.determine_best_guess_shell")
    @patch("commandrex.executor.platform_utils.get_shell_capabilities")
    def test_detect_shell_best_guess_fallback(
        self,
        mock_capabilities,
        mock_best_guess,
        mock_behavior_detect,
        mock_cmd_detect,
        mock_env_detect,
    ):
        """Test shell detection final fallback to best guess."""
        mock_env_detect.return_value = None
        mock_cmd_detect.return_value = None
        mock_behavior_detect.return_value = None
        mock_best_guess.return_value = ("bash", "5.0")
        mock_capabilities.return_value = {"supports_colors": True}

        result = detect_shell()

        assert result is not None
        assert result[0] == "bash"
        assert result[1] == "5.0"


class TestShellDetectionFromEnvironment:
    """Test cases for detect_shell_from_environment function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.get_parent_process_info")
    def test_detect_shell_windows_cmd_from_parent(
        self, mock_parent_info, mock_is_windows
    ):
        """Test CMD detection from parent process on Windows."""
        mock_is_windows.return_value = True
        mock_parent_info.return_value = ("cmd.exe", "C:\\Windows\\System32\\cmd.exe")

        result = detect_shell_from_environment()

        assert result is not None
        assert result[0] == "cmd"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.get_parent_process_info")
    @patch("subprocess.run")
    def test_detect_shell_windows_powershell_from_parent(
        self, mock_run, mock_parent_info, mock_is_windows
    ):
        """Test PowerShell detection from parent process on Windows."""
        mock_is_windows.return_value = True
        mock_parent_info.return_value = (
            "powershell.exe",
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        )

        mock_result = Mock()
        mock_result.stdout = "7.2.0"
        mock_run.return_value = mock_result

        result = detect_shell_from_environment()

        assert result is not None
        assert result[0] == "powershell"
        assert "7.2.0" in result[1]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ")
    def test_detect_shell_unix_from_bash_version(self, mock_environ, mock_is_windows):
        """Test bash detection from BASH_VERSION on Unix."""
        mock_is_windows.return_value = False
        mock_environ.get.side_effect = lambda key, default=None: {
            "BASH_VERSION": "5.1.8(1)-release"
        }.get(key, default)
        mock_environ.__contains__ = lambda self, key: key == "BASH_VERSION"

        result = detect_shell_from_environment()

        assert result is not None
        assert result[0] == "bash"
        assert "5.1.8" in result[1]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ")
    def test_detect_shell_unix_from_zsh_version(self, mock_environ, mock_is_windows):
        """Test zsh detection from ZSH_VERSION on Unix."""
        mock_is_windows.return_value = False
        mock_environ.get.side_effect = lambda key, default=None: {
            "ZSH_VERSION": "5.8"
        }.get(key, default)
        mock_environ.__contains__ = lambda self, key: key == "ZSH_VERSION"

        result = detect_shell_from_environment()

        assert result is not None
        assert result[0] == "zsh"
        assert result[1] == "5.8"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    @patch("commandrex.executor.platform_utils.get_shell_version")
    def test_detect_shell_from_shell_env_var(
        self, mock_get_version, mock_env_get, mock_is_windows
    ):
        """Test shell detection from SHELL environment variable."""
        mock_is_windows.return_value = False
        mock_env_get.side_effect = lambda key, default=None: {"SHELL": "/bin/zsh"}.get(
            key, default
        )
        mock_get_version.return_value = "5.8"

        result = detect_shell_from_environment()

        assert result is not None
        assert result[0] == "zsh"
        assert result[1] == "5.8"


class TestParentProcessInfo:
    """Test cases for get_parent_process_info function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_get_parent_process_info_windows_success(self, mock_run, mock_is_windows):
        """Test successful parent process detection on Windows."""
        mock_is_windows.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "powershell|C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        )
        mock_run.return_value = mock_result

        result = get_parent_process_info()

        assert result is not None
        assert result[0] == "powershell"
        assert "powershell.exe" in result[1]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_get_parent_process_info_windows_failure(self, mock_run, mock_is_windows):
        """Test parent process detection failure on Windows."""
        mock_is_windows.return_value = True
        mock_run.side_effect = Exception("Command failed")

        result = get_parent_process_info()

        assert result is None

    @patch("commandrex.executor.platform_utils.is_windows")
    def test_get_parent_process_info_unix(self, mock_is_windows):
        """Test parent process detection on Unix (not implemented)."""
        mock_is_windows.return_value = False

        result = get_parent_process_info()

        assert result is None


class TestShellDetectionFromCommands:
    """Test cases for detect_shell_from_commands function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_detect_shell_from_commands_windows_cmd(self, mock_run, mock_is_windows):
        """Test CMD detection from commands on Windows."""
        mock_is_windows.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Windows\\System32\\cmd.exe"
        mock_run.return_value = mock_result

        result = detect_shell_from_commands()

        assert result is not None
        assert result[0] == "cmd"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_detect_shell_from_commands_unix_bash(self, mock_run, mock_is_windows):
        """Test bash detection from commands on Unix."""
        mock_is_windows.return_value = False

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "GNU bash, version 5.1.8(1)-release"
        mock_run.return_value = mock_result

        result = detect_shell_from_commands()

        assert result is not None
        assert result[0] == "bash"
        assert "5.1.8" in result[1]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_detect_shell_from_commands_failure(self, mock_run, mock_is_windows):
        """Test shell detection failure from commands."""
        mock_is_windows.return_value = True
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        result = detect_shell_from_commands()

        assert result is None


class TestShellDetectionFromBehavior:
    """Test cases for detect_shell_from_behavior function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    @patch("commandrex.executor.platform_utils.get_shell_version")
    def test_detect_shell_from_behavior_windows_cmd(
        self, mock_get_version, mock_run, mock_is_windows
    ):
        """Test CMD detection from behavior on Windows."""
        mock_is_windows.return_value = True
        mock_get_version.return_value = "10.0.19041"

        # Mock successful CMD behavior tests
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Windows\\System32\\cmd.exe"
        mock_run.return_value = mock_result

        result = detect_shell_from_behavior()

        # Should return the shell with the most successful tests
        assert result is not None
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("subprocess.run")
    def test_detect_shell_from_behavior_no_matches(self, mock_run, mock_is_windows):
        """Test behavior detection when no shells match."""
        mock_is_windows.return_value = True
        mock_run.side_effect = Exception("Command failed")

        result = detect_shell_from_behavior()

        assert result is None


class TestBestGuessShell:
    """Test cases for determine_best_guess_shell function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.is_macos")
    @patch("sys.getwindowsversion")
    @patch("commandrex.executor.platform_utils.get_shell_version")
    def test_determine_best_guess_windows_10(
        self, mock_get_version, mock_win_version, mock_is_macos, mock_is_windows
    ):
        """Test best guess for Windows 10."""
        mock_is_windows.return_value = True
        mock_is_macos.return_value = False

        mock_version = Mock()
        mock_version.major = 10
        mock_win_version.return_value = mock_version
        mock_get_version.return_value = "7.2.0"

        result = determine_best_guess_shell()

        assert result[0] == "powershell"
        assert result[1] == "7.2.0"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.is_macos")
    @patch("platform.mac_ver")
    @patch("commandrex.executor.platform_utils.get_shell_version")
    def test_determine_best_guess_macos_catalina(
        self, mock_get_version, mock_mac_ver, mock_is_macos, mock_is_windows
    ):
        """Test best guess for macOS Catalina and later (zsh)."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True
        mock_mac_ver.return_value = ("10.15.7", "", "")
        mock_get_version.return_value = "5.8"

        result = determine_best_guess_shell()

        assert result[0] == "zsh"
        assert result[1] == "5.8"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.is_macos")
    @patch("commandrex.executor.platform_utils.get_shell_version")
    def test_determine_best_guess_linux(
        self, mock_get_version, mock_is_macos, mock_is_windows
    ):
        """Test best guess for Linux (bash)."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_get_version.return_value = "5.1.8"

        result = determine_best_guess_shell()

        assert result[0] == "bash"
        assert result[1] == "5.1.8"


class TestShellVersion:
    """Test cases for shell version detection functions."""

    @patch("subprocess.run")
    def test_get_shell_version_bash(self, mock_run):
        """Test getting bash version."""
        mock_result = Mock()
        mock_result.stdout = "GNU bash, version 5.1.8(1)-release (x86_64-pc-linux-gnu)"
        mock_run.return_value = mock_result

        version = get_shell_version("bash")

        assert version == "5.1.8(1)-release"

    @patch("subprocess.run")
    def test_get_shell_version_zsh(self, mock_run):
        """Test getting zsh version."""
        mock_result = Mock()
        mock_result.stdout = "zsh 5.8 (x86_64-apple-darwin20.0)"
        mock_run.return_value = mock_result

        version = get_shell_version("zsh")

        assert version == "5.8"

    @patch("subprocess.run")
    def test_get_shell_version_powershell(self, mock_run):
        """Test getting PowerShell version."""
        mock_result = Mock()
        mock_result.stdout = "7.2.0"
        mock_run.return_value = mock_result

        version = get_shell_version("powershell")

        assert version == "7.2.0"

    @patch("subprocess.run")
    def test_get_shell_version_cmd(self, mock_run):
        """Test getting CMD version."""
        mock_result = Mock()
        mock_result.stdout = "Microsoft Windows [Version 10.0.19041.1348]"
        mock_run.return_value = mock_result

        version = get_shell_version("cmd")

        assert version == "10.0.19041.1348"

    @patch("subprocess.run")
    def test_get_shell_version_failure(self, mock_run):
        """Test shell version detection failure."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        version = get_shell_version("bash")

        assert version == ""

    def test_parse_shell_version_bash(self):
        """Test parsing bash version output."""
        output = "GNU bash, version 5.1.8(1)-release (x86_64-pc-linux-gnu)"

        version = parse_shell_version("bash", output)

        assert version == "5.1.8(1)-release"

    def test_parse_shell_version_zsh(self):
        """Test parsing zsh version output."""
        output = "zsh 5.8 (x86_64-apple-darwin20.0)"

        version = parse_shell_version("zsh", output)

        assert version == "5.8"

    def test_parse_shell_version_powershell(self):
        """Test parsing PowerShell version output."""
        output = "7.2.0"

        version = parse_shell_version("powershell", output)

        assert version == "7.2.0"

    def test_parse_shell_version_cmd(self):
        """Test parsing CMD version output."""
        output = "Microsoft Windows [Version 10.0.19041.1348]"

        version = parse_shell_version("cmd", output)

        assert version == "10.0.19041.1348"

    def test_parse_shell_version_invalid(self):
        """Test parsing invalid version output."""
        output = "Invalid output"

        version = parse_shell_version("bash", output)

        assert version == ""


class TestShellCapabilities:
    """Test cases for get_shell_capabilities function."""

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_get_shell_capabilities_bash(self, mock_supports_ansi):
        """Test getting bash capabilities."""
        mock_supports_ansi.return_value = True

        capabilities = get_shell_capabilities("bash")

        assert capabilities["supports_redirection"] is True
        assert capabilities["supports_pipes"] is True
        assert capabilities["filename_completion"] is True
        assert capabilities["command_aliases"] is True
        assert capabilities["array_support"] is True
        assert capabilities["process_substitution"] is True
        assert capabilities["multiline_commands"] is True
        assert capabilities["command_history"] is True
        assert capabilities["command_editing"] is True

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_get_shell_capabilities_powershell(self, mock_supports_ansi):
        """Test getting PowerShell capabilities."""
        mock_supports_ansi.return_value = True

        capabilities = get_shell_capabilities("powershell")

        assert capabilities["filename_completion"] is True
        assert capabilities["command_aliases"] is True
        assert capabilities["array_support"] is True
        assert capabilities["process_substitution"] is False
        assert capabilities["object_pipeline"] is True
        assert capabilities["type_system"] is True

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_get_shell_capabilities_cmd(self, mock_supports_ansi):
        """Test getting CMD capabilities."""
        mock_supports_ansi.return_value = False

        capabilities = get_shell_capabilities("cmd")

        assert capabilities["filename_completion"] is True
        assert capabilities["command_aliases"] is False
        assert capabilities["array_support"] is False
        assert capabilities["process_substitution"] is False
        assert capabilities["multiline_commands"] is False
        assert capabilities["command_editing"] is False

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_get_shell_capabilities_fish(self, mock_supports_ansi):
        """Test getting fish capabilities."""
        mock_supports_ansi.return_value = True

        capabilities = get_shell_capabilities("fish")

        assert capabilities["filename_completion"] is True
        assert capabilities["command_aliases"] is True
        assert capabilities["array_support"] is True
        assert (
            capabilities["process_substitution"] is False
        )  # fish doesn't support process substitution
        assert capabilities["multiline_commands"] is True

    @patch("subprocess.run")
    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_get_shell_capabilities_bash_process_substitution_test(
        self, mock_supports_ansi, mock_run
    ):
        """Test bash process substitution capability testing."""
        mock_supports_ansi.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test"
        mock_run.return_value = mock_result

        capabilities = get_shell_capabilities("bash")

        assert capabilities["process_substitution"] is True


class TestUtilityFunctions:
    """Test cases for utility functions."""

    @patch("shutil.get_terminal_size")
    def test_get_terminal_size_success(self, mock_get_size):
        """Test successful terminal size detection."""
        # Mock the return value to be iterable like the real function
        mock_get_size.return_value = (120, 30)

        width, height = get_terminal_size()

        assert width == 120
        assert height == 30

    @patch("shutil.get_terminal_size")
    def test_get_terminal_size_fallback(self, mock_get_size):
        """Test terminal size fallback when detection fails."""
        mock_get_size.side_effect = OSError("No terminal")

        width, height = get_terminal_size()

        assert width == 80
        assert height == 24

    def test_normalize_path_basic(self):
        """Test basic path normalization."""
        path = normalize_path("./test/../documents")
        expected = os.path.normpath("documents")
        assert path == expected

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_normalize_path_with_user_and_vars(self, mock_expandvars, mock_expanduser):
        """Test path normalization with user directory and variables."""
        mock_expanduser.return_value = "/home/user/documents"
        mock_expandvars.return_value = "/home/user/documents"

        path = normalize_path("~/documents")

        assert path == os.path.normpath("/home/user/documents")

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_command_prefix_windows_powershell(
        self, mock_detect_shell, mock_is_windows
    ):
        """Test command prefix for PowerShell on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("powershell", "7.2.0", {})

        prefix = get_command_prefix()

        assert prefix == "powershell -Command"

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_command_prefix_windows_cmd(self, mock_detect_shell, mock_is_windows):
        """Test command prefix for CMD on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("cmd", "10.0", {})

        prefix = get_command_prefix()

        assert prefix == "cmd /c"

    @patch("commandrex.executor.platform_utils.is_windows")
    def test_get_command_prefix_unix(self, mock_is_windows):
        """Test command prefix for Unix systems."""
        mock_is_windows.return_value = False

        prefix = get_command_prefix()

        assert prefix == ""

    @patch("shutil.which")
    def test_find_executable_found(self, mock_which):
        """Test finding an executable that exists."""
        mock_which.return_value = "/usr/bin/python3"

        path = find_executable("python3")

        assert path == "/usr/bin/python3"

    @patch("shutil.which")
    def test_find_executable_not_found(self, mock_which):
        """Test finding an executable that doesn't exist."""
        mock_which.return_value = None

        path = find_executable("nonexistent")

        assert path is None


class TestCommandAdaptation:
    """Test cases for command adaptation functions."""

    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_adapt_command_for_powershell(self, mock_detect_shell):
        """Test command adaptation for PowerShell."""
        mock_detect_shell.return_value = ("powershell", "7.2.0", {})

        command = "ls -la"
        adapted = adapt_command_for_shell(command)

        assert "Get-ChildItem" in adapted

    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_adapt_command_for_cmd(self, mock_detect_shell):
        """Test command adaptation for CMD."""
        mock_detect_shell.return_value = ("cmd", "10.0", {})

        command = "ls -la"
        adapted = adapt_command_for_shell(command)

        assert "dir" in adapted

    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_adapt_command_for_bash(self, mock_detect_shell):
        """Test command adaptation for bash."""
        mock_detect_shell.return_value = ("bash", "5.1.8", {})

        command = "dir /w"
        adapted = adapt_command_for_shell(command)

        assert "ls" in adapted

    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_adapt_command_no_shell_detected(self, mock_detect_shell):
        """Test command adaptation when no shell is detected."""
        mock_detect_shell.return_value = None

        command = "ls -la"
        adapted = adapt_command_for_shell(command)

        assert adapted == command  # Should return unchanged


class TestShellStartupCommand:
    """Test cases for get_shell_startup_command function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_shell_startup_command_windows_powershell(
        self, mock_detect_shell, mock_is_windows
    ):
        """Test shell startup command for PowerShell on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("powershell", "7.2.0", {})

        command = get_shell_startup_command()

        assert command == ["powershell"]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_get_shell_startup_command_windows_cmd(
        self, mock_detect_shell, mock_is_windows
    ):
        """Test shell startup command for CMD on Windows."""
        mock_is_windows.return_value = True
        mock_detect_shell.return_value = ("cmd", "10.0", {})

        command = get_shell_startup_command()

        assert command == ["cmd"]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    def test_get_shell_startup_command_unix_with_shell_env(
        self, mock_env_get, mock_is_windows
    ):
        """Test shell startup command on Unix with SHELL environment variable."""
        mock_is_windows.return_value = False
        mock_env_get.return_value = "/bin/zsh"

        command = get_shell_startup_command()

        assert command == ["/bin/zsh"]

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    def test_get_shell_startup_command_unix_fallback(
        self, mock_env_get, mock_is_windows
    ):
        """Test shell startup command on Unix with fallback."""
        mock_is_windows.return_value = False
        # Mock os.environ.get to return the default value when SHELL is not set
        mock_env_get.side_effect = lambda key, default=None: (
            default if key == "SHELL" else None
        )

        command = get_shell_startup_command()

        assert command == ["/bin/sh"]


class TestAnsiColorSupport:
    """Test cases for supports_ansi_colors function."""

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    def test_supports_ansi_colors_windows_terminal(self, mock_env_get, mock_is_windows):
        """Test ANSI color support in Windows Terminal."""
        mock_is_windows.return_value = True
        mock_env_get.side_effect = lambda key, default=None: {
            "WT_SESSION": "some-session-id"
        }.get(key, default)

        assert supports_ansi_colors() is True

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("sys.getwindowsversion")
    def test_supports_ansi_colors_windows_10(self, mock_win_version, mock_is_windows):
        """Test ANSI color support on Windows 10."""
        mock_is_windows.return_value = True

        mock_version = Mock()
        mock_version.major = 10
        mock_win_version.return_value = mock_version

        assert supports_ansi_colors() is True

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    def test_supports_ansi_colors_ansicon(self, mock_env_get, mock_is_windows):
        """Test ANSI color support with ANSICON."""
        mock_is_windows.return_value = True
        mock_env_get.side_effect = lambda key, default=None: {"ANSICON": "1"}.get(
            key, default
        )

        assert supports_ansi_colors() is True

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    def test_supports_ansi_colors_term_env(self, mock_env_get, mock_is_windows):
        """Test ANSI color support with TERM environment variable."""
        mock_is_windows.return_value = True
        mock_env_get.side_effect = lambda key, default=None: {
            "TERM": "xterm-256color"
        }.get(key, default)

        assert supports_ansi_colors() is True

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    @patch("sys.getwindowsversion")
    def test_supports_ansi_colors_dumb_terminal(
        self, mock_win_version, mock_env_get, mock_is_windows
    ):
        """Test ANSI color support with dumb terminal."""
        mock_is_windows.return_value = True
        mock_env_get.side_effect = lambda key, default=None: {
            "TERM": "dumb",
            "WT_SESSION": None,
            "ANSICON": None,
        }.get(key, default)

        # Mock older Windows version that doesn't support ANSI
        mock_version = Mock()
        mock_version.major = 8
        mock_win_version.return_value = mock_version

        assert supports_ansi_colors() is False

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    @patch("sys.stdout.isatty")
    def test_supports_ansi_colors_unix_tty(
        self, mock_isatty, mock_env_get, mock_is_windows
    ):
        """Test ANSI color support on Unix with TTY."""
        mock_is_windows.return_value = False
        mock_env_get.side_effect = lambda key, default=None: {
            "TERM": "xterm-256color"
        }.get(key, default)
        mock_isatty.return_value = True

        assert supports_ansi_colors() is True

    @patch("commandrex.executor.platform_utils.is_windows")
    @patch("os.environ.get")
    @patch("sys.stdout.isatty")
    def test_supports_ansi_colors_unix_no_tty(
        self, mock_isatty, mock_env_get, mock_is_windows
    ):
        """Test ANSI color support on Unix without TTY."""
        mock_is_windows.return_value = False
        mock_env_get.return_value = None
        mock_isatty.return_value = False

        assert supports_ansi_colors() is False


class TestPlatformUtilsEdgeCases:
    """Test edge cases and error conditions."""

    def test_normalize_path_empty_string(self):
        """Test path normalization with empty string."""
        path = normalize_path("")
        # os.path.normpath("") returns "."
        assert path == "."

    def test_normalize_path_none_raises_error(self):
        """Test path normalization with None raises error."""
        with pytest.raises((TypeError, AttributeError)):
            normalize_path(None)

    @patch("commandrex.executor.platform_utils.detect_shell")
    def test_adapt_command_with_complex_command(self, mock_detect_shell):
        """Test command adaptation with complex command."""
        mock_detect_shell.return_value = ("powershell", "7.2.0", {})

        command = "ls -la | grep test > output.txt"
        adapted = adapt_command_for_shell(command)

        # Should contain PowerShell equivalents
        assert "Get-ChildItem" in adapted

    @patch("subprocess.run")
    def test_get_shell_version_timeout_handling(self, mock_run):
        """Test shell version detection with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["bash", "--version"], 2)

        version = get_shell_version("bash")

        assert version == ""

    @patch("commandrex.executor.platform_utils.detect_shell_from_environment")
    @patch("commandrex.executor.platform_utils.detect_shell_from_commands")
    @patch("commandrex.executor.platform_utils.detect_shell_from_behavior")
    @patch("commandrex.executor.platform_utils.determine_best_guess_shell")
    def test_detect_shell_all_methods_fail(
        self, mock_best_guess, mock_behavior, mock_commands, mock_env
    ):
        """Test shell detection when all methods fail."""
        mock_env.return_value = None
        mock_commands.return_value = None
        mock_behavior.return_value = None
        mock_best_guess.return_value = (None, "")

        result = detect_shell()

        assert result is None


@pytest.mark.integration
class TestPlatformUtilsIntegration:
    """Integration tests for platform utilities."""

    def test_real_platform_detection(self):
        """Test real platform detection."""
        info = get_platform_info()

        assert "os_name" in info
        assert info["os_name"] in ["Windows", "Darwin", "Linux"]
        assert "architecture" in info
        assert "python_version" in info

    def test_real_shell_detection(self):
        """Test real shell detection."""
        result = detect_shell()

        if result:
            shell_name, shell_version, capabilities = result
            expected_shells = ["powershell", "pwsh", "cmd", "bash", "zsh", "fish", "sh"]
            assert shell_name in expected_shells
            assert isinstance(capabilities, dict)

    def test_real_terminal_size_detection(self):
        """Test real terminal size detection."""
        width, height = get_terminal_size()

        assert width > 0
        assert height > 0
        assert isinstance(width, int)
        assert isinstance(height, int)

    def test_real_executable_finding(self):
        """Test finding real executables."""
        # Test with Python, which should be available
        python_path = find_executable("python") or find_executable("python3")

        if python_path:
            assert os.path.exists(python_path)

    def test_real_ansi_color_detection(self):
        """Test real ANSI color support detection."""
        supports_colors = supports_ansi_colors()

        assert isinstance(supports_colors, bool)

    def test_real_path_normalization(self):
        """Test real path normalization."""
        # Test with current directory
        path = normalize_path(".")
        assert os.path.exists(path)

        # Test with relative path
        path = normalize_path("./tests/../tests")
        expected = os.path.normpath("tests")
        assert path == expected
