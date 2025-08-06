from unittest.mock import patch

from commandrex.validator.command_validator import CommandValidator


class TestCommandValidator:
    def setup_method(self):
        self.validator = CommandValidator()

    #
    # Helper context managers to mock environment
    #
    def _mock_env(self, os_name: str, shell_name: str):
        """Patch platform and shell detection for the validator."""
        # Use direct patch() context managers rather than creating nested
        # patch objects. This avoids assigning a _patch object to the target
        # (which causes TypeError on call).
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(
            patch(
                "commandrex.executor.platform_utils.get_platform_info",
                return_value={"os_name": os_name},
            )
        )
        stack.enter_context(
            patch(
                "commandrex.executor.platform_utils.detect_shell",
                return_value=(shell_name, "1.0.0", {}),
            )
        )
        return stack

    #
    # CMD (Windows Command Prompt) tests
    #
    def test_cmd_rejects_unix_commands(self):
        with self._mock_env("Windows", "cmd"):
            res = self.validator.validate_for_environment("ls -la")
            assert not res.is_valid
            assert any("forbidden" in i.code for i in res.issues)

            res2 = self.validator.validate_for_environment("grep -r todo .")
            assert not res2.is_valid
            assert any("forbidden" in i.code for i in res2.issues)

    def test_cmd_path_separator_validation(self):
        with self._mock_env("Windows", "cmd"):
            # Wrong sep: forward slashes on Windows CMD
            res = self.validator.validate_for_environment("type ./logs/app.log")
            assert not res.is_valid
            assert any(i.code == "path_separator" for i in res.issues)

            # Right sep: backslashes is acceptable
            res_ok = self.validator.validate_for_environment(r"type C:\temp\file.txt")
            assert res_ok.is_valid

    def test_cmd_detects_unix_only_syntax(self):
        with self._mock_env("Windows", "cmd"):
            res = self.validator.validate_for_environment("sudo rm -rf C:\\temp")
            assert not res.is_valid
            assert any(i.code == "shell_syntax_mismatch" for i in res.issues)

    #
    # PowerShell tests
    #
    def test_powershell_rejects_unix_specific_tokens(self):
        with self._mock_env("Windows", "powershell"):
            res = self.validator.validate_for_environment("grep -r important .")
            assert not res.is_valid
            assert any("forbidden" in i.code for i in res.issues)

    def test_powershell_accepts_cmdlets(self):
        with self._mock_env("Windows", "powershell"):
            res = self.validator.validate_for_environment("Get-ChildItem -Path .")
            assert res.is_valid

    def test_powershell_path_separator_validation(self):
        with self._mock_env("Windows", "powershell"):
            # Wrong forward slash-only path
            res = self.validator.validate_for_environment("Get-Content ./logs/app.log")
            assert not res.is_valid
            assert any(i.code == "path_separator" for i in res.issues)

            res_ok = self.validator.validate_for_environment(
                r"Get-Content C:\logs\app.log"
            )
            assert res_ok.is_valid

    #
    # Bash tests (including Git Bash on Windows)
    #
    def test_bash_rejects_windows_commands(self):
        with self._mock_env("Linux", "bash"):
            res = self.validator.validate_for_environment("dir /a")
            assert not res.is_valid
            assert any("forbidden" in i.code for i in res.issues)

            res2 = self.validator.validate_for_environment("findstr /s todo *.txt")
            assert not res2.is_valid
            assert any("forbidden" in i.code for i in res2.issues)

    def test_bash_accepts_unix_commands(self):
        with self._mock_env("Linux", "bash"):
            res = self.validator.validate_for_environment("ls -la")
            assert res.is_valid

            res2 = self.validator.validate_for_environment("grep -r 'text' .")
            assert res2.is_valid

    def test_bash_path_separator_validation(self):
        with self._mock_env("Linux", "bash"):
            # Wrong sep: backslashes on Unix
            res = self.validator.validate_for_environment(r"cat C:\logs\app.log")
            assert not res.is_valid
            assert any(i.code == "path_separator" for i in res.issues)

            # Right sep: forward slashes
            res_ok = self.validator.validate_for_environment("cat ./logs/app.log")
            assert res_ok.is_valid

    #
    # Git Bash on Windows (bash shell + Windows OS)
    #
    def test_git_bash_treat_as_unix_shell(self):
        # Simulate Windows OS but bash shell (Git Bash)
        with self._mock_env("Windows", "bash"):
            res = self.validator.validate_for_environment("ls -la")
            assert res.is_valid

            res2 = self.validator.validate_for_environment("dir")
            assert not res2.is_valid
            assert any("forbidden" in i.code for i in res2.issues)

    #
    # Heuristic mismatches
    #
    def test_powershell_syntax_in_non_ps_shell(self):
        with self._mock_env("Linux", "bash"):
            res = self.validator.validate_for_environment("Get-ChildItem -Path .")
            assert not res.is_valid
            assert any(i.code == "shell_syntax_mismatch" for i in res.issues)

    def test_windows_shell_syntax_on_unix(self):
        with self._mock_env("Linux", "powershell"):
            # In reality, running PowerShell on Linux is possible,
            # but our heuristic aims to prevent accidental Windows-only usage
            self.validator.validate_for_environment("dir")
            # dir alone is not strictly forbidden for PowerShell, but the heuristic
            # for Windows-only shells on non-Windows OS should trigger if typical
            # patterns are detected (we include a PS hint)
            res2 = self.validator.validate_for_environment("Get-ChildItem")
            assert not res2.is_valid
            assert any(i.code == "os_shell_mismatch" for i in res2.issues)
