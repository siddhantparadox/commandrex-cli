"""
Command parser for CommandRex.

This module provides functions to parse, validate, and enhance
shell commands before execution.
"""

import re
import shlex
from typing import Dict, List, Optional, Tuple, Any

from commandrex.executor import platform_utils


class CommandParser:
    """
    Parser for shell commands.
    
    This class handles parsing, validation, and enhancement of
    shell commands before execution.
    """
    
    # Potentially dangerous command patterns
    DANGEROUS_PATTERNS = [
        # File deletion
        r"\brm\s+(-[rf]+\s+|.*-[^-]*[rf].*\s+)",  # rm with -r or -f flags
        r"\brmdir\s+/s",  # rmdir /s on Windows
        r"\bdel\s+/[fsq]",  # del with /f, /s, or /q on Windows
        
        # System modification
        r"\bchmod\s+777",  # chmod with overly permissive permissions
        r"\bsudo\b",  # sudo commands
        r"\bsu\b",  # su command
        r"\bformat\b",  # format command
        r"\bmkfs\b",  # mkfs command
        
        # Network operations
        r"\bcurl\s+.*\s+\|\s+sh",  # curl piped to shell
        r"\bwget\s+.*\s+\|\s+sh",  # wget piped to shell
        r"\bnc\b",  # netcat
        r"\bnetcat\b",  # netcat
        
        # Potentially destructive redirections
        r"\s+>\s+/dev/(null|zero|random)",  # Redirection to device files
        r"\s+>\s+/proc/",  # Redirection to proc
        r"\s+>\s+/sys/",  # Redirection to sys
        
        # Windows-specific dangerous commands
        r"\bformat\s+[a-zA-Z]:",  # Format drive
        r"\bdel\s+/[fsq].*\*\.[a-zA-Z0-9]+",  # Mass deletion with wildcards
    ]
    
    # Command patterns that require confirmation
    CONFIRMATION_PATTERNS = [
        # File operations
        r"\bmv\b",  # move files
        r"\bcp\b",  # copy files
        r"\bmove\b",  # Windows move
        r"\bcopy\b",  # Windows copy
        r"\brename\b",  # rename files
        
        # System operations
        r"\bshutdown\b",  # shutdown
        r"\breboot\b",  # reboot
        r"\brestart\b",  # restart
        
        # Network operations
        r"\bssh\b",  # ssh
        r"\bscp\b",  # scp
        r"\brsync\b",  # rsync
        
        # Package management
        r"\bapt(-get)?\s+(install|remove|purge)\b",  # apt operations
        r"\byum\s+(install|remove|erase)\b",  # yum operations
        r"\bdnf\s+(install|remove|erase)\b",  # dnf operations
        r"\bpacman\s+(-S|-R)\b",  # pacman operations
        r"\bpip\s+(install|uninstall)\b",  # pip operations
        r"\bnpm\s+(install|uninstall)\b",  # npm operations
    ]
    
    def __init__(self):
        """Initialize the command parser."""
        # Compile regex patterns for better performance
        self.dangerous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
        self.confirmation_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CONFIRMATION_PATTERNS]
    
    def parse_command(self, command: str) -> Tuple[str, List[str]]:
        """
        Parse a command string into command and arguments.
        
        Args:
            command (str): The command string to parse.
            
        Returns:
            Tuple[str, List[str]]: Tuple of (command, arguments).
        """
        if platform_utils.is_windows():
            # Windows-specific parsing logic
            if command.startswith("powershell ") or command.startswith("powershell.exe "):
                # Handle PowerShell commands differently
                parts = command.split(" ", 1)
                if len(parts) > 1:
                    return parts[0], ["-Command", parts[1]]
                return parts[0], []
            
            # For regular Windows commands
            try:
                parts = shlex.split(command)
                if parts:
                    return parts[0], parts[1:]
                return "", []
            except ValueError:
                # If shlex fails (e.g., with unclosed quotes), fall back to simple splitting
                parts = command.split()
                if parts:
                    return parts[0], parts[1:]
                return "", []
        else:
            # Unix-like systems
            try:
                parts = shlex.split(command)
                if parts:
                    return parts[0], parts[1:]
                return "", []
            except ValueError:
                # If shlex fails, fall back to simple splitting
                parts = command.split()
                if parts:
                    return parts[0], parts[1:]
                return "", []
    
    def is_dangerous(self, command: str) -> Tuple[bool, List[str]]:
        """
        Check if a command is potentially dangerous.
        
        Args:
            command (str): The command to check.
            
        Returns:
            Tuple[bool, List[str]]: Tuple of (is_dangerous, reasons).
        """
        reasons = []
        
        # Check against dangerous patterns
        for pattern in self.dangerous_patterns:
            if pattern.search(command):
                pattern_str = pattern.pattern
                reasons.append(f"Matches dangerous pattern: {pattern_str}")
        
        # Check for specific dangerous commands
        cmd_name, _ = self.parse_command(command)
        cmd_lower = cmd_name.lower()
        
        if cmd_lower in ["rm", "rmdir", "del", "format"]:
            reasons.append(f"Command '{cmd_name}' can delete files or format drives")
        
        if cmd_lower in ["chmod", "chown", "chgrp"] and "777" in command:
            reasons.append(f"Command '{cmd_name}' with permissive permissions (777)")
        
        if cmd_lower in ["sudo", "su", "runas"]:
            reasons.append(f"Command '{cmd_name}' elevates privileges")
        
        # Check for pipe to shell
        if " | sh" in command or " | bash" in command or " | zsh" in command:
            reasons.append("Command pipes output to a shell, which can be dangerous")
        
        # Check for redirection to sensitive locations
        if ">" in command:
            parts = command.split(">")
            if len(parts) > 1:
                redirect_target = parts[1].strip()
                if redirect_target.startswith("/dev/") or redirect_target.startswith("/proc/") or redirect_target.startswith("/sys/"):
                    reasons.append(f"Command redirects output to sensitive location: {redirect_target}")
        
        return bool(reasons), reasons
    
    def needs_confirmation(self, command: str) -> Tuple[bool, List[str]]:
        """
        Check if a command needs confirmation before execution.
        
        Args:
            command (str): The command to check.
            
        Returns:
            Tuple[bool, List[str]]: Tuple of (needs_confirmation, reasons).
        """
        reasons = []
        
        # Check if command is dangerous
        is_dangerous, dangerous_reasons = self.is_dangerous(command)
        if is_dangerous:
            reasons.extend(dangerous_reasons)
            return True, reasons
        
        # Check against confirmation patterns
        for pattern in self.confirmation_patterns:
            if pattern.search(command):
                pattern_str = pattern.pattern
                reasons.append(f"Matches pattern requiring confirmation: {pattern_str}")
        
        # Check for specific commands that need confirmation
        cmd_name, _ = self.parse_command(command)
        cmd_lower = cmd_name.lower()
        
        if cmd_lower in ["shutdown", "reboot", "restart", "halt", "poweroff"]:
            reasons.append(f"Command '{cmd_name}' affects system power state")
        
        if cmd_lower in ["ssh", "scp", "sftp", "rsync"]:
            reasons.append(f"Command '{cmd_name}' involves network operations")
        
        if cmd_lower in ["apt", "apt-get", "yum", "dnf", "pacman", "brew", "pip", "npm"]:
            reasons.append(f"Command '{cmd_name}' involves package management")
        
        return bool(reasons), reasons
    
    def validate_command(self, command: str) -> Dict[str, Any]:
        """
        Validate a command and provide detailed information.
        
        Args:
            command (str): The command to validate.
            
        Returns:
            Dict[str, Any]: Validation results.
        """
        result = {
            "command": command,
            "is_valid": True,
            "is_dangerous": False,
            "needs_confirmation": False,
            "reasons": [],
            "parsed_command": "",
            "parsed_args": [],
            "suggested_modifications": [],
        }
        
        # Basic validation
        if not command or command.isspace():
            result["is_valid"] = False
            result["reasons"].append("Command is empty")
            return result
        
        # Parse the command
        parsed_command, parsed_args = self.parse_command(command)
        result["parsed_command"] = parsed_command
        result["parsed_args"] = parsed_args
        
        if not parsed_command:
            result["is_valid"] = False
            result["reasons"].append("Could not parse command")
            return result
        
        # Check if command exists
        if not platform_utils.is_windows():
            # On Unix-like systems, we can use which to check if the command exists
            command_path = platform_utils.find_executable(parsed_command)
            if not command_path:
                result["is_valid"] = False
                result["reasons"].append(f"Command '{parsed_command}' not found")
                return result
        
        # Check if command is dangerous
        is_dangerous, dangerous_reasons = self.is_dangerous(command)
        result["is_dangerous"] = is_dangerous
        if is_dangerous:
            result["reasons"].extend(dangerous_reasons)
        
        # Check if command needs confirmation
        needs_confirmation, confirmation_reasons = self.needs_confirmation(command)
        result["needs_confirmation"] = needs_confirmation
        if needs_confirmation and not is_dangerous:  # Avoid duplicate reasons
            result["reasons"].extend(confirmation_reasons)
        
        # Suggest modifications for dangerous commands
        if is_dangerous:
            # For rm commands, suggest adding -i for interactive mode
            if parsed_command == "rm" and "-f" in command:
                result["suggested_modifications"].append(
                    command.replace("-f", "-i")
                )
            
            # For del commands, suggest adding /p for confirmation
            if parsed_command == "del" and "/q" in command:
                result["suggested_modifications"].append(
                    command.replace("/q", "/p")
                )
            
            # For chmod 777, suggest more restrictive permissions
            if parsed_command == "chmod" and "777" in command:
                result["suggested_modifications"].append(
                    command.replace("777", "755")
                )
        
        return result
    
    def enhance_command(self, command: str, platform_info: Optional[Dict[str, str]] = None) -> str:
        """
        Enhance a command with platform-specific optimizations.
        
        Args:
            command (str): The command to enhance.
            platform_info (Optional[Dict[str, str]]): Platform information.
            
        Returns:
            str: Enhanced command.
        """
        if not platform_info:
            platform_info = platform_utils.get_platform_info()
        
        os_name = platform_info.get("os_name", "").lower()
        shell_name = platform_info.get("shell_name", "").lower()
        
        # Apply platform-specific enhancements
        if os_name == "windows":
            # Windows-specific enhancements
            if command.startswith("ls "):
                # Replace Unix ls with Windows dir
                return command.replace("ls ", "dir ")
            
            if command.startswith("cat "):
                # Replace Unix cat with Windows type
                return command.replace("cat ", "type ")
            
            if shell_name in ["powershell", "pwsh"]:
                # PowerShell-specific enhancements
                if command.startswith("grep "):
                    # Replace grep with Select-String
                    return command.replace("grep ", "Select-String ")
                
                if command.startswith("rm "):
                    # Replace rm with Remove-Item
                    return command.replace("rm ", "Remove-Item ")
        
        elif os_name in ["darwin", "linux"]:
            # Unix-like enhancements
            if command.startswith("dir "):
                # Replace Windows dir with Unix ls
                return command.replace("dir ", "ls ")
            
            if command.startswith("type "):
                # Replace Windows type with Unix cat
                return command.replace("type ", "cat ")
        
        # Return the original command if no enhancements were applied
        return command
    
    def extract_command_components(self, command: str) -> List[Dict[str, str]]:
        """
        Extract and describe components of a command.
        
        Args:
            command (str): The command to analyze.
            
        Returns:
            List[Dict[str, str]]: List of command components with descriptions.
        """
        components = []
        
        # Parse the command
        cmd_name, args = self.parse_command(command)
        
        # Add the command name
        components.append({
            "part": cmd_name,
            "description": f"The main command to execute"
        })
        
        # Process arguments
        i = 0
        while i < len(args):
            arg = args[i]
            
            # Handle flags
            if arg.startswith("-"):
                description = "Command flag"
                
                # Check for common flags
                if arg in ["-r", "--recursive"]:
                    description = "Recursive operation flag"
                elif arg in ["-f", "--force"]:
                    description = "Force operation without confirmation"
                elif arg in ["-v", "--verbose"]:
                    description = "Verbose output flag"
                elif arg in ["-h", "--help"]:
                    description = "Help flag to display usage information"
                
                components.append({
                    "part": arg,
                    "description": description
                })
            
            # Handle input/output redirection
            elif arg in [">", ">>", "<", "|"]:
                descriptions = {
                    ">": "Output redirection (overwrites file)",
                    ">>": "Output redirection (appends to file)",
                    "<": "Input redirection (reads from file)",
                    "|": "Pipe output to another command"
                }
                
                components.append({
                    "part": arg,
                    "description": descriptions.get(arg, "Redirection operator")
                })
                
                # Add the next argument as the redirection target if available
                if i + 1 < len(args):
                    target_type = "file" if arg in [">", ">>", "<"] else "command"
                    components.append({
                        "part": args[i + 1],
                        "description": f"Target {target_type} for {arg} operation"
                    })
                    i += 1  # Skip the next argument since we've processed it
            
            # Handle other arguments
            else:
                # Try to determine if this is a file/directory path
                if "/" in arg or "\\" in arg or "." in arg:
                    components.append({
                        "part": arg,
                        "description": "File or directory path"
                    })
                else:
                    components.append({
                        "part": arg,
                        "description": "Command argument"
                    })
            
            i += 1
        
        return components
