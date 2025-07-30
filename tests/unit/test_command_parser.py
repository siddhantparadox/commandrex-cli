"""
Unit tests for commandrex.executor.command_parser module.

Tests the CommandParser class for parsing, validating, and enhancing
shell commands across different platforms.
"""

import pytest
from unittest.mock import patch, Mock

from commandrex.executor.command_parser import CommandParser
from commandrex.executor import platform_utils


class TestCommandParserInitialization:
    """Test cases for CommandParser initialization."""

    def test_parser_initialization(self):
        """Test that CommandParser initializes correctly."""
        parser = CommandParser()
        assert parser is not None
        assert hasattr(parser, 'dangerous_patterns')
        assert hasattr(parser, 'confirmation_patterns')
        assert len(parser.dangerous_patterns) > 0
        assert len(parser.confirmation_patterns) > 0

    def test_patterns_are_compiled(self):
        """Test that regex patterns are compiled during initialization."""
        parser = CommandParser()
        
        # Check that patterns are compiled regex objects
        for pattern in parser.dangerous_patterns:
            assert hasattr(pattern, 'search')
            assert hasattr(pattern, 'pattern')
        
        for pattern in parser.confirmation_patterns:
            assert hasattr(pattern, 'search')
            assert hasattr(pattern, 'pattern')


class TestParseCommand:
    """Test cases for parse_command method."""

    def test_parse_simple_command(self):
        """Test parsing simple command without arguments."""
        parser = CommandParser()
        cmd, args = parser.parse_command("ls")
        
        assert cmd == "ls"
        assert args == []

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        parser = CommandParser()
        cmd, args = parser.parse_command("ls -la /home")
        
        assert cmd == "ls"
        assert args == ["-la", "/home"]

    def test_parse_command_with_quotes(self):
        """Test parsing command with quoted arguments."""
        parser = CommandParser()
        cmd, args = parser.parse_command('echo "hello world"')
        
        assert cmd == "echo"
        assert args == ["hello world"]

    def test_parse_empty_command(self):
        """Test parsing empty command."""
        parser = CommandParser()
        cmd, args = parser.parse_command("")
        
        assert cmd == ""
        assert args == []

    def test_parse_whitespace_command(self):
        """Test parsing whitespace-only command."""
        parser = CommandParser()
        cmd, args = parser.parse_command("   ")
        
        assert cmd == ""
        assert args == []

    @patch.object(platform_utils, 'is_windows', return_value=True)
    def test_parse_powershell_command(self, mock_is_windows):
        """Test parsing PowerShell command on Windows."""
        parser = CommandParser()
        cmd, args = parser.parse_command("powershell Get-Process")
        
        assert cmd == "powershell"
        assert args == ["-Command", "Get-Process"]

    @patch.object(platform_utils, 'is_windows', return_value=True)
    def test_parse_powershell_exe_command(self, mock_is_windows):
        """Test parsing powershell.exe command on Windows."""
        parser = CommandParser()
        cmd, args = parser.parse_command("powershell.exe Get-ChildItem")
        
        assert cmd == "powershell.exe"
        assert args == ["-Command", "Get-ChildItem"]

    @patch.object(platform_utils, 'is_windows', return_value=False)
    def test_parse_unix_command(self, mock_is_windows):
        """Test parsing command on Unix-like systems."""
        parser = CommandParser()
        cmd, args = parser.parse_command("grep -r 'pattern' .")
        
        assert cmd == "grep"
        assert args == ["-r", "pattern", "."]

    def test_parse_command_with_malformed_quotes(self):
        """Test parsing command with malformed quotes."""
        parser = CommandParser()
        cmd, args = parser.parse_command('echo "unclosed quote')
        
        # Should handle gracefully by falling back to simple splitting
        assert cmd == "echo"
        assert len(args) >= 1

    def test_parse_complex_command(self):
        """Test parsing complex command with multiple arguments."""
        parser = CommandParser()
        cmd, args = parser.parse_command("find /home -name '*.py' -type f")
        
        assert cmd == "find"
        assert "/home" in args
        assert "*.py" in args
        assert "-name" in args
        assert "-type" in args
        assert "f" in args


class TestIsDangerous:
    """Test cases for is_dangerous method."""

    def test_safe_command(self):
        """Test that safe commands are not flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("ls -la")
        
        assert is_dangerous is False
        assert reasons == []

    def test_dangerous_rm_rf(self):
        """Test that rm -rf is flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("rm -rf /important/data")
        
        assert is_dangerous is True
        assert len(reasons) > 0
        assert any("rm" in reason.lower() for reason in reasons)

    def test_dangerous_chmod_777(self):
        """Test that chmod 777 is flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("chmod 777 /etc/passwd")
        
        assert is_dangerous is True
        assert len(reasons) > 0
        assert any("777" in reason for reason in reasons)

    def test_dangerous_sudo(self):
        """Test that sudo commands are flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("sudo rm file.txt")
        
        assert is_dangerous is True
        assert len(reasons) > 0
        assert any("sudo" in reason.lower() for reason in reasons)

    def test_dangerous_pipe_to_shell(self):
        """Test that piping to shell is flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("curl http://site.com | sh")
        
        assert is_dangerous is True
        assert len(reasons) > 0
        assert any("pipe" in reason.lower() for reason in reasons)

    def test_dangerous_redirection_to_dev(self):
        """Test that redirection to /dev/ is flagged as dangerous."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous("echo 'test' > /dev/sda")
        
        assert is_dangerous is True
        assert len(reasons) > 0
        assert any("/dev/" in reason for reason in reasons)

    @pytest.mark.parametrize("command", [
        "rm -rf /",
        "sudo rm -rf /home",
        "chmod 777 file",
        "format C:",
        "del /f /s /q *.*",
        "curl http://site.com | bash",
        "wget http://site.com | sh",
    ])
    def test_various_dangerous_commands(self, command):
        """Test various dangerous command patterns."""
        parser = CommandParser()
        is_dangerous, reasons = parser.is_dangerous(command)
        
        assert is_dangerous is True
        assert len(reasons) > 0


class TestNeedsConfirmation:
    """Test cases for needs_confirmation method."""

    def test_safe_command_no_confirmation(self):
        """Test that safe commands don't need confirmation."""
        parser = CommandParser()
        needs_conf, reasons = parser.needs_confirmation("ls -la")
        
        assert needs_conf is False
        assert reasons == []

    def test_dangerous_command_needs_confirmation(self):
        """Test that dangerous commands need confirmation."""
        parser = CommandParser()
        needs_conf, reasons = parser.needs_confirmation("rm -rf /")
        
        assert needs_conf is True
        assert len(reasons) > 0

    def test_mv_command_needs_confirmation(self):
        """Test that mv command needs confirmation."""
        parser = CommandParser()
        needs_conf, reasons = parser.needs_confirmation("mv file1.txt file2.txt")
        
        assert needs_conf is True
        assert len(reasons) > 0

    def test_shutdown_command_needs_confirmation(self):
        """Test that shutdown command needs confirmation."""
        parser = CommandParser()
        needs_conf, reasons = parser.needs_confirmation("shutdown -h now")
        
        assert needs_conf is True
        assert len(reasons) > 0
        assert any("power state" in reason.lower() for reason in reasons)

    def test_ssh_command_needs_confirmation(self):
        """Test that SSH command needs confirmation."""
        parser = CommandParser()
        needs_conf, reasons = parser.needs_confirmation("ssh user@server")
        
        assert needs_conf is True
        assert len(reasons) > 0
        assert any("network" in reason.lower() for reason in reasons)

    def test_package_management_needs_confirmation(self):
        """Test that package management commands need confirmation."""
        commands = [
            "apt install package",
            "yum remove package",
            "pip install package",
            "npm uninstall package"
        ]
        
        parser = CommandParser()
        for command in commands:
            needs_conf, reasons = parser.needs_confirmation(command)
            assert needs_conf is True
            assert len(reasons) > 0


class TestValidateCommand:
    """Test cases for validate_command method."""

    def test_validate_empty_command(self):
        """Test validation of empty command."""
        parser = CommandParser()
        result = parser.validate_command("")
        
        assert result["is_valid"] is False
        assert "empty" in result["reasons"][0].lower()

    def test_validate_whitespace_command(self):
        """Test validation of whitespace-only command."""
        parser = CommandParser()
        result = parser.validate_command("   ")
        
        assert result["is_valid"] is False
        assert "empty" in result["reasons"][0].lower()

    def test_validate_simple_safe_command(self):
        """Test validation of simple safe command."""
        parser = CommandParser()
        result = parser.validate_command("ls")
        
        assert result["is_valid"] is True
        assert result["is_dangerous"] is False
        assert result["needs_confirmation"] is False
        assert result["parsed_command"] == "ls"
        assert result["parsed_args"] == []

    def test_validate_dangerous_command(self):
        """Test validation of dangerous command."""
        parser = CommandParser()
        result = parser.validate_command("rm -rf /")
        
        assert result["is_valid"] is True  # Valid but dangerous
        assert result["is_dangerous"] is True
        assert result["needs_confirmation"] is True
        assert len(result["reasons"]) > 0

    @patch.object(platform_utils, 'find_executable', return_value=None)
    @patch.object(platform_utils, 'is_windows', return_value=False)
    def test_validate_nonexistent_command(self, mock_is_windows, mock_find_executable):
        """Test validation of non-existent command on Unix."""
        parser = CommandParser()
        result = parser.validate_command("nonexistent_command")
        
        assert result["is_valid"] is False
        assert any("not found" in reason for reason in result["reasons"])

    def test_validate_command_with_suggestions(self):
        """Test that dangerous commands get suggested modifications."""
        parser = CommandParser()
        result = parser.validate_command("rm -f important_file.txt")
        
        assert result["is_dangerous"] is True
        assert len(result["suggested_modifications"]) > 0
        assert any("-i" in suggestion for suggestion in result["suggested_modifications"])

    def test_validate_chmod_777_with_suggestions(self):
        """Test that chmod 777 gets safer suggestions."""
        parser = CommandParser()
        result = parser.validate_command("chmod 777 file.txt")
        
        assert result["is_dangerous"] is True
        assert len(result["suggested_modifications"]) > 0
        assert any("755" in suggestion for suggestion in result["suggested_modifications"])

    def test_validate_del_with_suggestions(self):
        """Test that Windows del /q gets safer suggestions."""
        parser = CommandParser()
        result = parser.validate_command("del /q file.txt")
        
        assert result["is_dangerous"] is True
        assert len(result["suggested_modifications"]) > 0
        assert any("/p" in suggestion for suggestion in result["suggested_modifications"])


class TestEnhanceCommand:
    """Test cases for enhance_command method."""

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_ls_on_windows(self, mock_platform_info):
        """Test enhancing ls command on Windows."""
        mock_platform_info.return_value = {
            "os_name": "windows",
            "shell_name": "cmd"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("ls -la")
        
        assert enhanced == "dir -la"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_cat_on_windows(self, mock_platform_info):
        """Test enhancing cat command on Windows."""
        mock_platform_info.return_value = {
            "os_name": "windows",
            "shell_name": "cmd"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("cat file.txt")
        
        assert enhanced == "type file.txt"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_grep_on_powershell(self, mock_platform_info):
        """Test enhancing grep command on PowerShell."""
        mock_platform_info.return_value = {
            "os_name": "windows",
            "shell_name": "powershell"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("grep pattern file.txt")
        
        assert enhanced == "Select-String pattern file.txt"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_rm_on_powershell(self, mock_platform_info):
        """Test enhancing rm command on PowerShell."""
        mock_platform_info.return_value = {
            "os_name": "windows",
            "shell_name": "powershell"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("rm file.txt")
        
        assert enhanced == "Remove-Item file.txt"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_dir_on_unix(self, mock_platform_info):
        """Test enhancing dir command on Unix."""
        mock_platform_info.return_value = {
            "os_name": "linux",
            "shell_name": "bash"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("dir /home")
        
        assert enhanced == "ls /home"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_type_on_unix(self, mock_platform_info):
        """Test enhancing type command on Unix."""
        mock_platform_info.return_value = {
            "os_name": "darwin",
            "shell_name": "zsh"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("type file.txt")
        
        assert enhanced == "cat file.txt"

    @patch.object(platform_utils, 'get_platform_info')
    def test_enhance_no_change_needed(self, mock_platform_info):
        """Test that commands that don't need enhancement are unchanged."""
        mock_platform_info.return_value = {
            "os_name": "linux",
            "shell_name": "bash"
        }
        
        parser = CommandParser()
        enhanced = parser.enhance_command("echo 'hello world'")
        
        assert enhanced == "echo 'hello world'"


class TestExtractCommandComponents:
    """Test cases for extract_command_components method."""

    def test_extract_simple_command_components(self):
        """Test extracting components from simple command."""
        parser = CommandParser()
        components = parser.extract_command_components("ls")
        
        assert len(components) == 1
        assert components[0]["part"] == "ls"
        assert "command" in components[0]["description"].lower()

    def test_extract_command_with_flags(self):
        """Test extracting components from command with flags."""
        parser = CommandParser()
        components = parser.extract_command_components("ls -la")
        
        assert len(components) == 2
        assert components[0]["part"] == "ls"
        assert components[1]["part"] == "-la"
        assert "flag" in components[1]["description"].lower()

    def test_extract_command_with_verbose_flag(self):
        """Test extracting components with verbose flag."""
        parser = CommandParser()
        components = parser.extract_command_components("ls -v")
        
        verbose_component = next((c for c in components if c["part"] == "-v"), None)
        assert verbose_component is not None
        assert "verbose" in verbose_component["description"].lower()

    def test_extract_command_with_help_flag(self):
        """Test extracting components with help flag."""
        parser = CommandParser()
        components = parser.extract_command_components("ls --help")
        
        help_component = next((c for c in components if c["part"] == "--help"), None)
        assert help_component is not None
        assert "help" in help_component["description"].lower()

    def test_extract_command_with_redirection(self):
        """Test extracting components with output redirection."""
        parser = CommandParser()
        components = parser.extract_command_components("ls > output.txt")
        
        # Should have ls, >, and output.txt
        assert len(components) == 3
        redirect_component = next((c for c in components if c["part"] == ">"), None)
        assert redirect_component is not None
        assert "redirection" in redirect_component["description"].lower()

    def test_extract_command_with_pipe(self):
        """Test extracting components with pipe."""
        parser = CommandParser()
        components = parser.extract_command_components("ls | grep txt")
        
        pipe_component = next((c for c in components if c["part"] == "|"), None)
        assert pipe_component is not None
        assert "pipe" in pipe_component["description"].lower()

    def test_extract_command_with_file_paths(self):
        """Test extracting components with file paths."""
        parser = CommandParser()
        components = parser.extract_command_components("cat /home/user/file.txt")
        
        path_component = next((c for c in components if "/" in c["part"]), None)
        assert path_component is not None
        assert "path" in path_component["description"].lower()

    def test_extract_complex_command_components(self):
        """Test extracting components from complex command."""
        parser = CommandParser()
        components = parser.extract_command_components("find /home -name '*.py' -type f")
        
        assert len(components) > 4
        assert components[0]["part"] == "find"
        
        # Check that all parts are accounted for
        parts = [c["part"] for c in components]
        assert "/home" in parts
        assert "-name" in parts
        assert "*.py" in parts
        assert "-type" in parts
        assert "f" in parts


class TestCommandParserEdgeCases:
    """Test edge cases and error conditions."""

    def test_parse_command_with_unicode(self):
        """Test parsing command with unicode characters."""
        parser = CommandParser()
        cmd, args = parser.parse_command("echo 'héllo wörld'")
        
        assert cmd == "echo"
        assert len(args) == 1
        assert "héllo wörld" in args[0]

    def test_very_long_command(self):
        """Test parsing very long command."""
        parser = CommandParser()
        long_arg = "a" * 1000
        cmd, args = parser.parse_command(f"echo {long_arg}")
        
        assert cmd == "echo"
        assert args[0] == long_arg

    def test_command_with_special_characters(self):
        """Test parsing command with special characters."""
        parser = CommandParser()
        cmd, args = parser.parse_command("echo '$HOME && echo $USER'")
        
        assert cmd == "echo"
        assert len(args) == 1

    def test_validate_command_with_none_input(self):
        """Test validation with None input."""
        parser = CommandParser()
        
        with pytest.raises((TypeError, AttributeError)):
            parser.validate_command(None)

    def test_is_dangerous_with_case_variations(self):
        """Test dangerous command detection with case variations."""
        parser = CommandParser()
        
        commands = [
            "RM -rf /",
            "Sudo rm file",
            "CHMOD 777 file",
            "Format C:"
        ]
        
        for command in commands:
            is_dangerous, reasons = parser.is_dangerous(command)
            assert is_dangerous is True, f"Command '{command}' should be flagged as dangerous"


@pytest.mark.unit
class TestCommandParserIntegration:
    """Integration tests for CommandParser functionality."""

    def test_full_command_processing_pipeline(self):
        """Test complete command processing from parse to enhance."""
        parser = CommandParser()
        command = "ls -la /home"
        
        # Parse
        cmd, args = parser.parse_command(command)
        assert cmd == "ls"
        assert args == ["-la", "/home"]
        
        # Validate
        result = parser.validate_command(command)
        assert result["is_valid"] is True
        assert result["is_dangerous"] is False
        
        # Extract components
        components = parser.extract_command_components(command)
        assert len(components) == 3
        
        # Enhance (should be no-op for this command on Unix)
        with patch.object(platform_utils, 'get_platform_info') as mock_info:
            mock_info.return_value = {"os_name": "linux", "shell_name": "bash"}
            enhanced = parser.enhance_command(command)
            assert enhanced == command

    def test_dangerous_command_full_analysis(self):
        """Test full analysis of dangerous command."""
        parser = CommandParser()
        command = "rm -rf /important/data"
        
        # Should be flagged as dangerous
        is_dangerous, reasons = parser.is_dangerous(command)
        assert is_dangerous is True
        assert len(reasons) > 0
        
        # Should need confirmation
        needs_conf, conf_reasons = parser.needs_confirmation(command)
        assert needs_conf is True
        
        # Validation should reflect danger
        result = parser.validate_command(command)
        assert result["is_dangerous"] is True
        assert result["needs_confirmation"] is True
        assert len(result["suggested_modifications"]) > 0

    def test_cross_platform_command_enhancement(self):
        """Test command enhancement across different platforms."""
        parser = CommandParser()
        command = "ls -la"
        
        # Test on Windows
        with patch.object(platform_utils, 'get_platform_info') as mock_info:
            mock_info.return_value = {"os_name": "windows", "shell_name": "cmd"}
            enhanced = parser.enhance_command(command)
            assert enhanced == "dir -la"
        
        # Test on Unix
        with patch.object(platform_utils, 'get_platform_info') as mock_info:
            mock_info.return_value = {"os_name": "linux", "shell_name": "bash"}
            enhanced = parser.enhance_command(command)
            assert enhanced == command  # No change needed