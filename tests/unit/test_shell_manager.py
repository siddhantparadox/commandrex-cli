"""
Unit tests for commandrex.executor.shell_manager module.

Tests shell execution, process management, and cross-platform shell handling.
"""

import os
import sys
import pytest
import asyncio
import time
from unittest.mock import patch, Mock, MagicMock, AsyncMock
import subprocess
import threading

from commandrex.executor.shell_manager import (
    ShellManager,
    CommandResult
)


class TestCommandResult:
    """Test cases for CommandResult class."""

    def test_command_result_creation(self):
        """Test CommandResult initialization."""
        result = CommandResult(
            command="ls -la",
            return_code=0,
            stdout="file1.txt\nfile2.txt",
            stderr="",
            duration=1.5
        )
        
        assert result.command == "ls -la"
        assert result.return_code == 0
        assert result.stdout == "file1.txt\nfile2.txt"
        assert result.stderr == ""
        assert result.duration == 1.5
        assert result.success is True
        assert result.terminated is False

    def test_command_result_failure(self):
        """Test CommandResult with failure."""
        result = CommandResult(
            command="invalid_command",
            return_code=1,
            stdout="",
            stderr="command not found",
            duration=0.1
        )
        
        assert result.success is False
        assert result.return_code == 1
        assert result.stderr == "command not found"

    def test_command_result_terminated(self):
        """Test CommandResult with terminated flag."""
        result = CommandResult(
            command="long_running_command",
            return_code=-15,
            stdout="partial output",
            stderr="",
            duration=5.0,
            terminated=True
        )
        
        assert result.terminated is True
        assert result.success is False

    def test_command_result_to_dict(self):
        """Test CommandResult to_dict method."""
        result = CommandResult("test", 0, "output", "error", 1.0)
        result_dict = result.to_dict()
        
        assert result_dict["command"] == "test"
        assert result_dict["return_code"] == 0
        assert result_dict["stdout"] == "output"
        assert result_dict["stderr"] == "error"
        assert result_dict["duration"] == 1.0
        assert result_dict["success"] is True
        assert result_dict["terminated"] is False

    def test_command_result_string_representation(self):
        """Test CommandResult string representation."""
        result = CommandResult("test", 0, "output", "", 1.0)
        str_repr = str(result)
        
        assert "test" in str_repr
        assert "Success" in str_repr
        assert "1.00s" in str_repr
        assert "output" in str_repr

    def test_command_result_string_representation_failure(self):
        """Test CommandResult string representation for failure."""
        result = CommandResult("test", 1, "", "error", 1.0)
        str_repr = str(result)
        
        assert "Failed (code 1)" in str_repr
        assert "error" in str_repr

    def test_command_result_string_representation_terminated(self):
        """Test CommandResult string representation for terminated."""
        result = CommandResult("test", -15, "", "", 1.0, terminated=True)
        str_repr = str(result)
        
        assert "Terminated" in str_repr


class TestShellManager:
    """Test cases for ShellManager class."""

    def test_shell_manager_initialization(self):
        """Test ShellManager initialization."""
        manager = ShellManager()
        
        assert manager.command_parser is not None
        assert isinstance(manager.active_processes, dict)
        assert manager._next_process_id == 1
        assert manager._lock is not None

    def test_get_next_process_id(self):
        """Test process ID generation."""
        manager = ShellManager()
        
        id1 = manager._get_next_process_id()
        id2 = manager._get_next_process_id()
        id3 = manager._get_next_process_id()
        
        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

    def test_get_next_process_id_thread_safety(self):
        """Test process ID generation thread safety."""
        manager = ShellManager()
        ids = []
        
        def get_id():
            ids.append(manager._get_next_process_id())
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_id)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All IDs should be unique
        assert len(set(ids)) == 10
        assert min(ids) == 1
        assert max(ids) == 10

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    def test_prepare_command_windows_simple(self, mock_is_windows):
        """Test command preparation on Windows."""
        mock_is_windows.return_value = True
        
        manager = ShellManager()
        result = manager._prepare_command("dir")
        
        assert result == "dir"

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    @patch('commandrex.executor.shell_manager.platform_utils.find_executable')
    def test_prepare_command_windows_powershell(self, mock_find_executable, mock_is_windows):
        """Test PowerShell command preparation on Windows."""
        mock_is_windows.return_value = True
        mock_find_executable.return_value = "pwsh.exe"
        
        manager = ShellManager()
        result = manager._prepare_command("Get-Process")
        
        assert "pwsh -Command" in result
        assert "Get-Process" in result

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    @patch('commandrex.executor.shell_manager.platform_utils.find_executable')
    def test_prepare_command_windows_powershell_fallback(self, mock_find_executable, mock_is_windows):
        """Test PowerShell command preparation fallback."""
        mock_is_windows.return_value = True
        mock_find_executable.return_value = None  # pwsh not available
        
        manager = ShellManager()
        result = manager._prepare_command("Get-Process")
        
        assert "powershell -Command" in result
        assert "Get-Process" in result

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    def test_prepare_command_unix_simple(self, mock_is_windows):
        """Test command preparation on Unix."""
        mock_is_windows.return_value = False
        
        manager = ShellManager()
        result = manager._prepare_command("ls -la")
        
        assert isinstance(result, list)
        assert result == ["ls", "-la"]

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    def test_prepare_command_unix_complex_quotes(self, mock_is_windows):
        """Test command preparation with complex quotes on Unix."""
        mock_is_windows.return_value = False
        
        manager = ShellManager()
        result = manager._prepare_command("echo 'unclosed quote")
        
        # Should fall back to string when shlex fails
        assert result == "echo 'unclosed quote"

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    def test_get_shell_args_windows(self, mock_is_windows):
        """Test shell arguments for Windows."""
        mock_is_windows.return_value = True
        
        manager = ShellManager()
        args = manager._get_shell_args()
        
        assert args == {"shell": True}

    @patch('commandrex.executor.shell_manager.platform_utils.is_windows')
    def test_get_shell_args_unix(self, mock_is_windows):
        """Test shell arguments for Unix."""
        mock_is_windows.return_value = False
        
        manager = ShellManager()
        args = manager._get_shell_args()
        
        assert args == {"shell": False}

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test successful command execution."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout.readline = AsyncMock(side_effect=[
                b"Hello World\n",
                b""  # EOF
            ])
            mock_process.stderr.readline = AsyncMock(side_effect=[
                b""  # EOF
            ])
            mock_process.wait = AsyncMock(return_value=0)
            mock_create.return_value = mock_process
            
            result = await manager.execute_command("echo 'Hello World'")
            
            assert result.success is True
            assert result.return_code == 0
            assert "Hello World" in result.stdout
            assert result.command == "echo 'Hello World'"
            assert result.duration > 0

    @pytest.mark.asyncio
    async def test_execute_command_failure(self):
        """Test failed command execution."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[
                b"command not found\n",
                b""  # EOF
            ])
            mock_process.wait = AsyncMock(return_value=1)
            mock_create.return_value = mock_process
            
            result = await manager.execute_command("invalid_command")
            
            assert result.success is False
            assert result.return_code == 1
            assert "command not found" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_command_with_timeout(self):
        """Test command execution with timeout."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.terminate = AsyncMock()
            mock_process.kill = AsyncMock()
            mock_create.return_value = mock_process
            
            with pytest.raises(asyncio.TimeoutError):
                await manager.execute_command("sleep 10", timeout=1.0)
            
            mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command_with_callbacks(self):
        """Test command execution with output callbacks."""
        manager = ShellManager()
        stdout_lines = []
        stderr_lines = []
        
        def stdout_callback(line):
            stdout_lines.append(line)
        
        def stderr_callback(line):
            stderr_lines.append(line)
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout.readline = AsyncMock(side_effect=[
                b"line 1\n",
                b"line 2\n",
                b""  # EOF
            ])
            mock_process.stderr.readline = AsyncMock(side_effect=[
                b"error line\n",
                b""  # EOF
            ])
            mock_process.wait = AsyncMock(return_value=0)
            mock_create.return_value = mock_process
            
            result = await manager.execute_command(
                "test command",
                stdout_callback=stdout_callback,
                stderr_callback=stderr_callback
            )
            
            assert result.success is True
            assert len(stdout_lines) == 2
            assert "line 1" in stdout_lines[0]
            assert "line 2" in stdout_lines[1]
            assert len(stderr_lines) == 1
            assert "error line" in stderr_lines[0]

    @pytest.mark.asyncio
    async def test_execute_command_with_environment(self):
        """Test command execution with custom environment."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_create.return_value = mock_process
            
            env = {"TEST_VAR": "test_value"}
            await manager.execute_command("echo $TEST_VAR", env=env)
            
            call_args = mock_create.call_args
            assert "TEST_VAR" in call_args[1]['env']
            assert call_args[1]['env']['TEST_VAR'] == "test_value"

    @pytest.mark.asyncio
    async def test_execute_command_with_cwd(self):
        """Test command execution with working directory."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_create.return_value = mock_process
            
            await manager.execute_command("pwd", cwd="/tmp")
            
            call_args = mock_create.call_args
            assert call_args[1]['cwd'] == "/tmp"

    @pytest.mark.asyncio
    async def test_execute_command_safely_valid(self):
        """Test safe command execution with valid command."""
        manager = ShellManager()
        
        with patch.object(manager.command_parser, 'validate_command') as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "is_dangerous": False,
                "reasons": []
            }
            
            with patch.object(manager, 'execute_command') as mock_execute:
                mock_result = CommandResult("test", 0, "output", "", 1.0)
                mock_execute.return_value = mock_result
                
                result, validation_info = await manager.execute_command_safely("test command")
                
                assert result.success is True
                assert validation_info["is_valid"] is True
                assert validation_info["is_dangerous"] is False

    @pytest.mark.asyncio
    async def test_execute_command_safely_invalid(self):
        """Test safe command execution with invalid command."""
        manager = ShellManager()
        
        with patch.object(manager.command_parser, 'validate_command') as mock_validate:
            mock_validate.return_value = {
                "is_valid": False,
                "is_dangerous": False,
                "reasons": ["Invalid syntax"]
            }
            
            with pytest.raises(ValueError) as exc_info:
                await manager.execute_command_safely("invalid command")
            
            assert "Invalid command" in str(exc_info.value)
            assert "Invalid syntax" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_command_safely_dangerous(self):
        """Test safe command execution with dangerous command."""
        manager = ShellManager()
        
        with patch.object(manager.command_parser, 'validate_command') as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "is_dangerous": True,
                "reasons": ["Potentially destructive"]
            }
            
            with pytest.raises(ValueError) as exc_info:
                await manager.execute_command_safely("rm -rf /")
            
            assert "Dangerous command" in str(exc_info.value)
            assert "Potentially destructive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_command_safely_no_validation(self):
        """Test safe command execution with validation disabled."""
        manager = ShellManager()
        
        with patch.object(manager, 'execute_command') as mock_execute:
            mock_result = CommandResult("test", 0, "output", "", 1.0)
            mock_execute.return_value = mock_result
            
            result, validation_info = await manager.execute_command_safely(
                "test command", 
                validate=False
            )
            
            assert result.success is True
            assert validation_info == {}

    def test_terminate_all_processes(self):
        """Test terminating all active processes."""
        manager = ShellManager()
        
        # Add some mock processes
        mock_process1 = Mock()
        mock_process2 = Mock()
        mock_process3 = Mock()
        
        manager.active_processes[1] = mock_process1
        manager.active_processes[2] = mock_process2
        manager.active_processes[3] = mock_process3
        
        manager.terminate_all_processes()
        
        mock_process1.terminate.assert_called_once()
        mock_process2.terminate.assert_called_once()
        mock_process3.terminate.assert_called_once()
        
        assert len(manager.active_processes) == 0

    def test_terminate_all_processes_with_error(self):
        """Test terminating processes when some fail."""
        manager = ShellManager()
        
        mock_process1 = Mock()
        mock_process2 = Mock()
        mock_process2.terminate.side_effect = OSError("Process already dead")
        
        manager.active_processes[1] = mock_process1
        manager.active_processes[2] = mock_process2
        
        # Should not raise exception
        manager.terminate_all_processes()
        
        assert len(manager.active_processes) == 0

    def test_terminate_process_success(self):
        """Test terminating a specific process successfully."""
        manager = ShellManager()
        
        mock_process = Mock()
        manager.active_processes[1] = mock_process
        
        result = manager.terminate_process(1)
        
        assert result is True
        mock_process.terminate.assert_called_once()
        assert 1 not in manager.active_processes

    def test_terminate_process_not_found(self):
        """Test terminating a non-existent process."""
        manager = ShellManager()
        
        result = manager.terminate_process(999)
        
        assert result is False

    def test_terminate_process_with_error(self):
        """Test terminating a process that fails."""
        manager = ShellManager()
        
        mock_process = Mock()
        mock_process.terminate.side_effect = OSError("Process already dead")
        manager.active_processes[1] = mock_process
        
        result = manager.terminate_process(1)
        
        assert result is False
        assert 1 not in manager.active_processes

    def test_get_active_processes_empty(self):
        """Test getting active processes when none exist."""
        manager = ShellManager()
        
        processes = manager.get_active_processes()
        
        assert processes == {}

    def test_get_active_processes_with_processes(self):
        """Test getting active processes information."""
        manager = ShellManager()
        
        mock_process1 = Mock()
        mock_process1.pid = 1234
        mock_process1.returncode = None  # Still running
        
        mock_process2 = Mock()
        mock_process2.pid = 5678
        mock_process2.returncode = 0  # Finished
        
        manager.active_processes[1] = mock_process1
        manager.active_processes[2] = mock_process2
        
        processes = manager.get_active_processes()
        
        assert len(processes) == 2
        assert processes[1]["pid"] == 1234
        assert processes[1]["running"] is True
        assert processes[2]["pid"] == 5678
        assert processes[2]["running"] is False


class TestShellManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_prepare_command_powershell_patterns(self):
        """Test PowerShell command pattern detection."""
        manager = ShellManager()
        
        powershell_commands = [
            "Get-Process",
            "Set-Location",
            "New-Item",
            "Remove-Item",
            "$variable = 'test'",
            "Write-Output 'hello'"
        ]
        
        with patch('commandrex.executor.shell_manager.platform_utils.is_windows', return_value=True):
            with patch('commandrex.executor.shell_manager.platform_utils.find_executable', return_value="pwsh.exe"):
                for cmd in powershell_commands:
                    result = manager._prepare_command(cmd)
                    assert "pwsh -Command" in result
                    assert cmd in result

    @pytest.mark.asyncio
    async def test_execute_command_process_registration(self):
        """Test that processes are properly registered and unregistered."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_create.return_value = mock_process
            
            await manager.execute_command("test")
            
            # Process should be unregistered after completion
            assert len(manager.active_processes) == 0

    @pytest.mark.asyncio
    async def test_execute_command_force_kill_on_timeout(self):
        """Test force killing process when terminate doesn't work."""
        manager = ShellManager()
        
        with patch('asyncio.create_subprocess_shell') as mock_create:
            mock_process = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            
            # First wait call times out, second wait call (after terminate) also times out
            mock_process.wait = AsyncMock(side_effect=[
                asyncio.TimeoutError(),  # Initial timeout
                asyncio.TimeoutError(),  # Timeout after terminate
                0  # Success after kill
            ])
            mock_process.terminate = AsyncMock()
            mock_process.kill = AsyncMock()
            mock_create.return_value = mock_process
            
            with pytest.raises(asyncio.TimeoutError):
                await manager.execute_command("sleep 10", timeout=1.0)
            
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()


@pytest.mark.integration
class TestShellManagerIntegration:
    """Integration tests for ShellManager."""

    @pytest.mark.asyncio
    async def test_real_command_execution_safe(self):
        """Test real command execution with safe commands."""
        manager = ShellManager()
        
        # Use a safe command that works on all platforms
        if sys.platform.startswith('win'):
            result = await manager.execute_command("echo test")
        else:
            result = await manager.execute_command("echo test")
        
        assert result.success is True
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_real_command_with_output_callback(self):
        """Test real command execution with output callback."""
        manager = ShellManager()
        output_lines = []
        
        def callback(line):
            output_lines.append(line)
        
        if sys.platform.startswith('win'):
            result = await manager.execute_command("echo line1 & echo line2", stdout_callback=callback)
        else:
            result = await manager.execute_command("echo line1; echo line2", stdout_callback=callback)
        
        assert result.success is True
        assert len(output_lines) > 0

    @pytest.mark.asyncio
    async def test_real_working_directory(self):
        """Test command execution with real working directory."""
        import tempfile
        
        manager = ShellManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            if sys.platform.startswith('win'):
                result = await manager.execute_command("cd", cwd=temp_dir)
            else:
                result = await manager.execute_command("pwd", cwd=temp_dir)
            
            assert result.success is True
            # Output should contain the temp directory path
            assert temp_dir in result.stdout or temp_dir.replace('/', '\\') in result.stdout