"""
Shell manager for CommandRex.

This module provides functions to safely execute shell commands
and stream their output in real-time.
"""

import asyncio
import os
import re
import signal
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from commandrex.executor import platform_utils
from commandrex.executor.command_parser import CommandParser


class CommandResult:
    """Class to store command execution results."""
    
    def __init__(
        self,
        command: str,
        return_code: int,
        stdout: str,
        stderr: str,
        duration: float,
        terminated: bool = False
    ):
        """
        Initialize the command result.
        
        Args:
            command (str): The executed command.
            return_code (int): The command return code.
            stdout (str): Standard output from the command.
            stderr (str): Standard error from the command.
            duration (float): Execution duration in seconds.
            terminated (bool): Whether the command was terminated.
        """
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.terminated = terminated
    
    @property
    def success(self) -> bool:
        """
        Check if the command executed successfully.
        
        Returns:
            bool: True if return code is 0, False otherwise.
        """
        return self.return_code == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the result.
        """
        return {
            "command": self.command,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "terminated": self.terminated,
            "success": self.success
        }
    
    def __str__(self) -> str:
        """
        Get a string representation of the result.
        
        Returns:
            str: String representation.
        """
        status = "Success" if self.success else f"Failed (code {self.return_code})"
        if self.terminated:
            status = "Terminated"
        
        return (
            f"Command: {self.command}\n"
            f"Status: {status}\n"
            f"Duration: {self.duration:.2f}s\n"
            f"Output: {self.stdout[:500]}{'...' if len(self.stdout) > 500 else ''}\n"
            f"Errors: {self.stderr[:500]}{'...' if len(self.stderr) > 500 else ''}"
        )


class ShellManager:
    """
    Manager for shell command execution.
    
    This class handles the safe execution of shell commands,
    with real-time output streaming and proper error handling.
    """
    
    def __init__(self):
        """Initialize the shell manager."""
        self.command_parser = CommandParser()
        self.active_processes: Dict[int, subprocess.Popen] = {}
        self._next_process_id = 1
        self._lock = threading.Lock()
    
    def _get_next_process_id(self) -> int:
        """
        Get the next available process ID.
        
        Returns:
            int: Next process ID.
        """
        with self._lock:
            process_id = self._next_process_id
            self._next_process_id += 1
            return process_id
    
    def _prepare_command(self, command: str) -> Union[str, List[str]]:
        """
        Prepare a command for execution based on the platform.
        
        Args:
            command (str): The command to prepare.
            
        Returns:
            Union[str, List[str]]: Prepared command.
        """
        # Check if this is a PowerShell command
        is_powershell_command = False
        
        # Common PowerShell cmdlet patterns
        powershell_patterns = [
            r'^Get-\w+',
            r'^Set-\w+',
            r'^New-\w+',
            r'^Remove-\w+',
            r'^Add-\w+',
            r'^Import-\w+',
            r'^Export-\w+',
            r'^Invoke-\w+',
            r'^Test-\w+',
            r'^Update-\w+',
            r'^ConvertTo-\w+',
            r'^ConvertFrom-\w+',
            r'^\$\w+',  # PowerShell variables
            r'^Write-\w+',
        ]
        
        # Check if the command matches any PowerShell pattern
        for pattern in powershell_patterns:
            if re.match(pattern, command.strip()):
                is_powershell_command = True
                break
        
        # Get shell information
        shell_info = platform_utils.detect_shell()
        current_shell = shell_info[0] if shell_info else ""
        
        if platform_utils.is_windows():
            # Always use PowerShell for PowerShell commands on Windows
            if is_powershell_command:
                # Check if pwsh is available first (PowerShell Core)
                if platform_utils.find_executable("pwsh"):
                    return f"pwsh -Command \"{command}\""
                else:
                    return f"powershell -Command \"{command}\""
            
            # On Windows, we need to use shell=True or cmd /c
            return command
        else:
            # On Unix-like systems, we can use shell=False with a list
            # This is safer as it avoids shell injection
            try:
                import shlex
                return shlex.split(command)
            except ValueError:
                # If shlex fails (e.g., with unclosed quotes), fall back to shell=True
                return command
    
    def _get_shell_args(self) -> Dict[str, Any]:
        """
        Get the appropriate shell arguments for the current platform.
        
        Returns:
            Dict[str, Any]: Shell arguments.
        """
        if platform_utils.is_windows():
            return {"shell": True}
        else:
            return {"shell": False}
    
    async def execute_command(
        self,
        command: str,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> CommandResult:
        """
        Execute a shell command asynchronously.
        
        Args:
            command (str): The command to execute.
            stdout_callback (Optional[Callable]): Callback for stdout.
            stderr_callback (Optional[Callable]): Callback for stderr.
            timeout (Optional[float]): Timeout in seconds.
            cwd (Optional[str]): Working directory.
            env (Optional[Dict[str, str]]): Environment variables.
            
        Returns:
            CommandResult: Command execution result.
            
        Raises:
            asyncio.TimeoutError: If the command times out.
            OSError: If the command cannot be executed.
        """
        import time
        start_time = time.time()
        
        # Prepare the command
        prepared_command = self._prepare_command(command)
        shell_args = self._get_shell_args()
        
        # Merge environment variables
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        
        # Create process
        process = await asyncio.create_subprocess_shell(
            prepared_command,  # Use the prepared command instead of the original
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=merged_env,
            **shell_args
        ) if isinstance(prepared_command, str) else await asyncio.create_subprocess_exec(
            *prepared_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=merged_env
        )
        
        # Register the process
        process_id = self._get_next_process_id()
        self.active_processes[process_id] = process
        
        # Collect output
        stdout_chunks = []
        stderr_chunks = []
        
        # Define output handlers
        async def read_stream(stream, chunks, callback):
            while True:
                line = await stream.readline()
                if not line:
                    break
                
                line_str = line.decode("utf-8", errors="replace")
                chunks.append(line_str)
                
                if callback:
                    callback(line_str)
        
        # Start reading streams
        try:
            # Set up tasks for reading stdout and stderr
            stdout_task = asyncio.create_task(
                read_stream(process.stdout, stdout_chunks, stdout_callback)
            )
            stderr_task = asyncio.create_task(
                read_stream(process.stderr, stderr_chunks, stderr_callback)
            )
            
            # Wait for the process to complete or timeout
            terminated = False
            try:
                if timeout:
                    # Wait for the process with timeout
                    await asyncio.wait_for(process.wait(), timeout)
                else:
                    # Wait for the process without timeout
                    await process.wait()
            
            except asyncio.TimeoutError:
                # Terminate the process if it times out
                process.terminate()
                try:
                    # Give it a chance to terminate gracefully
                    await asyncio.wait_for(process.wait(), 2.0)
                except asyncio.TimeoutError:
                    # Force kill if it doesn't terminate
                    process.kill()
                    await process.wait()
                
                terminated = True
                raise asyncio.TimeoutError(f"Command timed out after {timeout} seconds")
            
            finally:
                # Wait for stdout and stderr tasks to complete
                await stdout_task
                await stderr_task
        
        finally:
            # Unregister the process
            if process_id in self.active_processes:
                del self.active_processes[process_id]
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Combine output chunks
        stdout_output = "".join(stdout_chunks)
        stderr_output = "".join(stderr_chunks)
        
        # Create and return result
        return CommandResult(
            command=command,
            return_code=process.returncode,
            stdout=stdout_output,
            stderr=stderr_output,
            duration=duration,
            terminated=terminated
        )
    
    def terminate_all_processes(self) -> None:
        """Terminate all active processes."""
        with self._lock:
            for process_id, process in list(self.active_processes.items()):
                try:
                    process.terminate()
                except OSError:
                    # Process might have already exited
                    pass
                
                # Remove from active processes
                if process_id in self.active_processes:
                    del self.active_processes[process_id]
    
    def terminate_process(self, process_id: int) -> bool:
        """
        Terminate a specific process.
        
        Args:
            process_id (int): ID of the process to terminate.
            
        Returns:
            bool: True if terminated successfully, False otherwise.
        """
        with self._lock:
            if process_id in self.active_processes:
                process = self.active_processes[process_id]
                try:
                    process.terminate()
                    del self.active_processes[process_id]
                    return True
                except OSError:
                    # Process might have already exited
                    if process_id in self.active_processes:
                        del self.active_processes[process_id]
                    return False
            
            return False
    
    async def execute_command_safely(
        self,
        command: str,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        validate: bool = True
    ) -> Tuple[CommandResult, Dict[str, Any]]:
        """
        Execute a command with safety validation.
        
        Args:
            command (str): The command to execute.
            stdout_callback (Optional[Callable]): Callback for stdout.
            stderr_callback (Optional[Callable]): Callback for stderr.
            timeout (Optional[float]): Timeout in seconds.
            cwd (Optional[str]): Working directory.
            env (Optional[Dict[str, str]]): Environment variables.
            validate (bool): Whether to validate the command.
            
        Returns:
            Tuple[CommandResult, Dict[str, Any]]: Command result and validation info.
            
        Raises:
            ValueError: If the command is invalid or dangerous.
            asyncio.TimeoutError: If the command times out.
            OSError: If the command cannot be executed.
        """
        validation_info = {}
        
        if validate:
            # Validate the command
            validation_info = self.command_parser.validate_command(command)
            
            if not validation_info["is_valid"]:
                reasons = ", ".join(validation_info["reasons"])
                raise ValueError(f"Invalid command: {reasons}")
            
            if validation_info["is_dangerous"]:
                reasons = ", ".join(validation_info["reasons"])
                raise ValueError(f"Dangerous command: {reasons}")
        
        # Execute the command
        result = await self.execute_command(
            command,
            stdout_callback,
            stderr_callback,
            timeout,
            cwd,
            env
        )
        
        return result, validation_info
    
    def get_active_processes(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about active processes.
        
        Returns:
            Dict[int, Dict[str, Any]]: Dictionary of process information.
        """
        with self._lock:
            processes = {}
            for process_id, process in self.active_processes.items():
                processes[process_id] = {
                    "pid": process.pid,
                    "returncode": process.returncode,
                    "running": process.returncode is None
                }
            return processes
