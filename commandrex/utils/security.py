"""
Security utilities for CommandRex.

This module provides functions for command safety analysis,
secure storage of sensitive information, and other security utilities.
"""

import os
import re
import shlex
from typing import Dict, List, Optional, Tuple, Any

# Import from our own modules
from commandrex.executor import platform_utils
from commandrex.utils.logging import get_logger

# Set up logger
logger = get_logger("utils.security")


class CommandSafetyAnalyzer:
    """
    Analyzer for command safety.
    
    This class provides methods to analyze the safety of shell commands,
    identifying potentially dangerous operations and suggesting safer alternatives.
    """
    
    # Patterns for dangerous operations
    DANGEROUS_PATTERNS = [
        # File deletion
        (r"\brm\s+(-[rf]+\s+|.*-[^-]*[rf].*\s+)", "File deletion with rm -r or -f"),
        (r"\brmdir\s+/s", "Directory deletion with rmdir /s"),
        (r"\bdel\s+/[fsq]", "File deletion with del /f, /s, or /q"),
        
        # System modification
        (r"\bchmod\s+777", "Overly permissive file permissions (chmod 777)"),
        (r"\bsudo\b", "Privileged command execution (sudo)"),
        (r"\bsu\b", "Switch user command (su)"),
        (r"\bformat\b", "Disk formatting command"),
        (r"\bmkfs\b", "Filesystem creation command"),
        
        # Network operations
        (r"\bcurl\s+.*\s+\|\s+sh", "Piping curl output to shell"),
        (r"\bwget\s+.*\s+\|\s+sh", "Piping wget output to shell"),
        (r"\bnc\b", "Netcat command"),
        (r"\bnetcat\b", "Netcat command"),
        
        # Potentially destructive redirections
        (r"\s+>\s+/dev/(null|zero|random)", "Redirection to device files"),
        (r"\s+>\s+/proc/", "Redirection to proc filesystem"),
        (r"\s+>\s+/sys/", "Redirection to sys filesystem"),
        
        # Windows-specific dangerous commands
        (r"\bformat\s+[a-zA-Z]:", "Disk formatting command"),
        (r"\bdel\s+/[fsq].*\*\.[a-zA-Z0-9]+", "Mass file deletion with wildcards"),
    ]
    
    # Commands that require special attention
    SENSITIVE_COMMANDS = {
        "rm": "File deletion",
        "rmdir": "Directory deletion",
        "del": "File deletion (Windows)",
        "format": "Disk formatting",
        "chmod": "Change file permissions",
        "chown": "Change file ownership",
        "dd": "Disk operations",
        "mkfs": "Create filesystem",
        "fdisk": "Partition disk",
        "shutdown": "System shutdown",
        "reboot": "System reboot",
        "halt": "System halt",
        "poweroff": "System power off",
        "sudo": "Privileged command execution",
        "su": "Switch user",
    }
    
    def __init__(self):
        """Initialize the command safety analyzer."""
        # Compile regex patterns for better performance
        self.dangerous_patterns = [(re.compile(pattern, re.IGNORECASE), description) 
                                  for pattern, description in self.DANGEROUS_PATTERNS]
    
    def analyze_command(self, command: str) -> Dict[str, Any]:
        """
        Analyze a command for safety concerns.
        
        Args:
            command (str): The command to analyze.
            
        Returns:
            Dict[str, Any]: Analysis results.
        """
        result = {
            "command": command,
            "is_safe": True,
            "risk_level": "none",
            "concerns": [],
            "recommendations": [],
            "safer_alternatives": [],
        }
        
        # Skip analysis for empty commands
        if not command or command.isspace():
            return result
        
        # Check against dangerous patterns
        for pattern, description in self.dangerous_patterns:
            if pattern.search(command):
                result["is_safe"] = False
                result["concerns"].append(description)
        
        # Parse the command to check the base command
        try:
            cmd_parts = shlex.split(command)
            if not cmd_parts:
                return result
            
            base_cmd = cmd_parts[0].lower()
            
            # Check if the base command is in our sensitive list
            if base_cmd in self.SENSITIVE_COMMANDS:
                # Add as a concern if not already identified
                description = self.SENSITIVE_COMMANDS[base_cmd]
                if description not in result["concerns"]:
                    result["concerns"].append(description)
                
                # Command-specific analysis
                if base_cmd == "rm":
                    self._analyze_rm_command(command, cmd_parts, result)
                elif base_cmd == "chmod":
                    self._analyze_chmod_command(command, cmd_parts, result)
                elif base_cmd == "dd":
                    self._analyze_dd_command(command, cmd_parts, result)
                elif base_cmd in ["shutdown", "reboot", "halt", "poweroff"]:
                    self._analyze_power_command(command, cmd_parts, result)
                elif base_cmd in ["sudo", "su"]:
                    self._analyze_privilege_command(command, cmd_parts, result)
        
        except ValueError:
            # If shlex fails, consider it potentially unsafe
            result["is_safe"] = False
            result["concerns"].append("Command parsing failed, potentially malformed command")
        
        # Determine risk level based on concerns
        if not result["concerns"]:
            result["risk_level"] = "none"
        elif len(result["concerns"]) == 1 and not any(c in " ".join(result["concerns"]).lower() 
                                                    for c in ["deletion", "format", "privileged"]):
            result["risk_level"] = "low"
        elif any(c in " ".join(result["concerns"]).lower() for c in ["privileged", "sudo", "su"]):
            result["risk_level"] = "high"
        else:
            result["risk_level"] = "medium"
        
        # Update is_safe based on risk level
        if result["risk_level"] != "none":
            result["is_safe"] = False
        
        return result
    
    def _analyze_rm_command(self, command: str, cmd_parts: List[str], result: Dict[str, Any]) -> None:
        """
        Analyze rm command for safety concerns.
        
        Args:
            command (str): The full command.
            cmd_parts (List[str]): Parsed command parts.
            result (Dict[str, Any]): Analysis results to update.
        """
        # Check for recursive flag
        has_recursive = False
        has_force = False
        
        for part in cmd_parts[1:]:
            if part.startswith("-"):
                if "r" in part or "R" in part:
                    has_recursive = True
                if "f" in part:
                    has_force = True
        
        if has_recursive:
            result["concerns"].append("Recursive deletion (-r or -R flag)")
        
        if has_force:
            result["concerns"].append("Forced deletion without confirmation (-f flag)")
        
        # Check for wildcard usage
        if "*" in command:
            result["concerns"].append("Wildcard deletion (may delete more files than intended)")
        
        # Suggest safer alternatives
        if has_force:
            safer_cmd = command.replace(" -f", " -i").replace("-rf", "-ri").replace("-fr", "-ir")
            result["safer_alternatives"].append(safer_cmd)
            result["recommendations"].append("Use -i flag for interactive confirmation instead of -f")
        
        if not has_recursive and not has_force:
            result["recommendations"].append("Consider using -i flag for interactive confirmation")
    
    def _analyze_chmod_command(self, command: str, cmd_parts: List[str], result: Dict[str, Any]) -> None:
        """
        Analyze chmod command for safety concerns.
        
        Args:
            command (str): The full command.
            cmd_parts (List[str]): Parsed command parts.
            result (Dict[str, Any]): Analysis results to update.
        """
        # Check for overly permissive permissions
        for part in cmd_parts[1:]:
            if part == "777" or part == "a+rwx":
                result["concerns"].append("Overly permissive file permissions (777 or a+rwx)")
                result["recommendations"].append("Consider more restrictive permissions like 755 for directories or 644 for files")
                
                # Suggest safer alternatives
                if part == "777":
                    result["safer_alternatives"].append(command.replace("777", "755"))
                elif part == "a+rwx":
                    result["safer_alternatives"].append(command.replace("a+rwx", "u+rwx,go+rx"))
    
    def _analyze_dd_command(self, command: str, cmd_parts: List[str], result: Dict[str, Any]) -> None:
        """
        Analyze dd command for safety concerns.
        
        Args:
            command (str): The full command.
            cmd_parts (List[str]): Parsed command parts.
            result (Dict[str, Any]): Analysis results to update.
        """
        # Check for disk operations
        for i, part in enumerate(cmd_parts):
            if part.startswith("if=") or part.startswith("of="):
                device_path = part.split("=", 1)[1]
                if device_path.startswith("/dev/"):
                    result["concerns"].append(f"Direct disk operation on device {device_path}")
                    result["risk_level"] = "high"
                    result["recommendations"].append("Be extremely careful with dd operations on device files")
    
    def _analyze_power_command(self, command: str, cmd_parts: List[str], result: Dict[str, Any]) -> None:
        """
        Analyze power-related commands for safety concerns.
        
        Args:
            command (str): The full command.
            cmd_parts (List[str]): Parsed command parts.
            result (Dict[str, Any]): Analysis results to update.
        """
        # All power commands are potentially disruptive
        result["concerns"].append("System power state change (may interrupt work)")
        result["recommendations"].append("Ensure all work is saved before executing this command")
        
        # Check for immediate shutdown
        if "now" in cmd_parts or "-t 0" in command:
            result["concerns"].append("Immediate shutdown without delay")
            
            # Suggest safer alternatives
            if "-t 0" in command:
                result["safer_alternatives"].append(command.replace("-t 0", "-t 60"))
                result["recommendations"].append("Consider adding a time delay with -t to allow for preparation")
    
    def _analyze_privilege_command(self, command: str, cmd_parts: List[str], result: Dict[str, Any]) -> None:
        """
        Analyze privilege escalation commands for safety concerns.
        
        Args:
            command (str): The full command.
            cmd_parts (List[str]): Parsed command parts.
            result (Dict[str, Any]): Analysis results to update.
        """
        # All privilege escalation commands are high risk
        result["concerns"].append("Privilege escalation (may allow unrestricted system access)")
        result["risk_level"] = "high"
        
        # For sudo, check what command is being run with elevated privileges
        if cmd_parts[0] == "sudo" and len(cmd_parts) > 1:
            elevated_cmd = cmd_parts[1]
            if elevated_cmd in self.SENSITIVE_COMMANDS:
                result["concerns"].append(f"Running sensitive command '{elevated_cmd}' with elevated privileges")
            
            # Recursive analysis of the command being run with sudo
            if len(cmd_parts) > 1:
                elevated_cmd_str = " ".join(cmd_parts[1:])
                elevated_analysis = self.analyze_command(elevated_cmd_str)
                
                # Add concerns from the elevated command
                for concern in elevated_analysis["concerns"]:
                    if concern not in result["concerns"]:
                        result["concerns"].append(f"Elevated: {concern}")
        
        result["recommendations"].append("Use privilege escalation only when absolutely necessary")
        result["recommendations"].append("Consider using more specific permissions or a non-root user if possible")


def sanitize_command(command: str) -> str:
    """
    Sanitize a command to remove potentially harmful elements.
    
    Args:
        command (str): The command to sanitize.
        
    Returns:
        str: Sanitized command.
    """
    # Remove shell control operators
    sanitized = re.sub(r'[;&|><`$]', '', command)
    
    # Remove quotes
    sanitized = sanitized.replace('"', '').replace("'", '')
    
    # Remove newlines and control characters
    sanitized = re.sub(r'[\r\n\t\f\v]', ' ', sanitized)
    
    # Remove multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def secure_string(value: str) -> str:
    """
    Securely mask a sensitive string for display or logging.
    
    Args:
        value (str): The sensitive string to mask.
        
    Returns:
        str: Masked string.
    """
    if not value:
        return ""
    
    # Show only first and last character, mask the rest
    if len(value) <= 4:
        return "*" * len(value)
    else:
        return value[0] + "*" * (len(value) - 2) + value[-1]


# Global instance of the command safety analyzer
safety_analyzer = CommandSafetyAnalyzer()
