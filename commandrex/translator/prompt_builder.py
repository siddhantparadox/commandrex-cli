"""
Prompt builder for CommandRex.

This module provides functions to build effective prompts for the OpenAI API,
incorporating system information, command history, and user preferences.
"""

import json
from typing import Any, Dict, List, Optional

from commandrex.executor import platform_utils


class PromptBuilder:
    """
    Builder for creating effective prompts for command translation.

    This class handles the construction of prompts that incorporate
    system information, command history, and user preferences to
    generate accurate command translations.
    """

    def __init__(self):
        """Initialize the prompt builder."""
        # Base system prompts
        self.base_system_prompt = self.build_enhanced_system_prompt()

        self.safety_prompt = (
            "IMPORTANT SAFETY GUIDELINES:\n"
            "- Never generate commands that could harm the user's system\n"
            "- Flag commands that delete files, modify system settings, "
            "or have network impact\n"
            "- Provide clear warnings for potentially dangerous operations\n"
            "- Suggest safer alternatives when appropriate\n"
            "- Always explain what a command will do before the user executes it\n"
        )

        # Platform-specific prompt templates
        self.platform_prompts = {
            "windows": (
                "The user is on a Windows system. Use Windows-compatible commands.\n"
                "- Prefer PowerShell commands when appropriate\n"
                "- Use CMD commands when simpler or more universal\n"
                "- Use correct path separators (backslashes)\n"
                "- Consider Windows-specific tools and utilities\n"
            ),
            "macos": (
                "The user is on a macOS system. Use macOS-compatible commands.\n"
                "- Use Unix-style commands\n"
                "- Consider macOS-specific tools like Homebrew\n"
                "- Use correct path separators (forward slashes)\n"
                "- Be aware of macOS file system peculiarities\n"
            ),
            "linux": (
                "The user is on a Linux system. Use Linux-compatible commands.\n"
                "- Use standard Unix commands\n"
                "- Consider the common Linux tools and utilities\n"
                "- Use correct path separators (forward slashes)\n"
                "- Be aware of different package managers for different distributions\n"
            ),
        }

        # Shell-specific prompt templates
        self.shell_prompts = {
            "bash": "The user is using Bash shell. Use Bash syntax for commands.",
            "zsh": "The user is using Zsh shell. Use Zsh syntax for commands.",
            "powershell": "The user is using PowerShell. Use PowerShell cmdlets "
            "and syntax.",
            "cmd": "The user is using Windows Command Prompt. Use CMD syntax "
            "for commands.",
        }

        # Platform-specific shell overrides
        self.platform_shell_overrides = {
            "windows": {
                "bash": (
                    "The user is using Git Bash on Windows. Use Unix/Bash commands, "
                    "NOT PowerShell or CMD commands.\n"
                    "- Use standard Unix commands like ls, grep, cat, etc.\n"
                    "- Use forward slashes for paths, not backslashes\n"
                    "- Remember that Git Bash is a Unix-like environment on Windows\n"
                    "- Do NOT use PowerShell cmdlets or CMD commands\n"
                )
            }
        }

    # Strict environment rules to prevent cross-shell/OS mistakes
    STRICT_ENVIRONMENT_RULES = {
        "cmd": {
            "forbidden_commands": [
                "ls",
                "grep",
                "cat",
                "chmod",
                "chown",
                "find",
                "which",
                "man",
                "sudo",
                "tar",
            ],
            "required_syntax": {
                "list_files": "dir",
                "search_text": "findstr",
                "view_file": "type",
                "path_separator": "\\",
            },
            "wrong_separator": "/",
        },
        "powershell": {
            # Note: PowerShell has aliases for ls/cat/grep, but require explicit cmdlets
            "forbidden_commands": [
                "grep",
                "cat",
                "sed",
                "awk",
                "chmod",
                "chown",
                "rm ",
                "mv ",
                "cp ",
                "sudo",
            ],
            "required_syntax": {
                "list_files": "Get-ChildItem",
                "search_text": "Select-String",
                "view_file": "Get-Content",
                "path_separator": "\\",
            },
            "wrong_separator": "/",
        },
        "pwsh": {
            "forbidden_commands": [
                "grep",
                "cat",
                "sed",
                "awk",
                "chmod",
                "chown",
                "rm ",
                "mv ",
                "cp ",
                "sudo",
            ],
            "required_syntax": {
                "list_files": "Get-ChildItem",
                "search_text": "Select-String",
                "view_file": "Get-Content",
                "path_separator": "\\",
            },
            "wrong_separator": "/",
        },
        "bash": {
            "forbidden_commands": [
                "dir",
                "type ",
                "findstr",
                "cls",
                "powershell",
                "pwsh",
            ],
            "required_syntax": {
                "list_files": "ls",
                "search_text": "grep",
                "view_file": "cat",
                "path_separator": "/",
            },
            "wrong_separator": "\\",
        },
        "zsh": {
            "forbidden_commands": [
                "dir",
                "type ",
                "findstr",
                "cls",
                "powershell",
                "pwsh",
            ],
            "required_syntax": {
                "list_files": "ls",
                "search_text": "grep",
                "view_file": "cat",
                "path_separator": "/",
            },
            "wrong_separator": "\\",
        },
        "fish": {
            "forbidden_commands": [
                "dir",
                "type ",
                "findstr",
                "cls",
                "powershell",
                "pwsh",
            ],
            "required_syntax": {
                "list_files": "ls",
                "search_text": "grep",
                "view_file": "cat",
                "path_separator": "/",
            },
            "wrong_separator": "\\",
        },
    }

    def _get_platform_prompt(self) -> str:
        """
        Get the appropriate platform-specific prompt.

        Returns:
            str: Platform-specific prompt.
        """
        # Check if we're in Git Bash on Windows
        shell_info = platform_utils.detect_shell()
        if platform_utils.is_windows() and shell_info and shell_info[0] == "bash":
            return (
                "The user is on Windows but using Git Bash (a Unix-like environment).\n"
                "- Use Unix-style commands, NOT Windows commands\n"
                "- Use forward slashes for paths, not backslashes\n"
                "- Use standard Unix commands like ls, grep, find, etc.\n"
                "- Do NOT use PowerShell cmdlets or CMD commands\n"
            )

        # Standard platform detection
        if platform_utils.is_windows():
            return self.platform_prompts["windows"]
        elif platform_utils.is_macos():
            return self.platform_prompts["macos"]
        elif platform_utils.is_linux():
            return self.platform_prompts["linux"]
        else:
            # Default to a generic prompt
            return "Use commands compatible with standard Unix-like systems."

    def _get_shell_prompt(self) -> str:
        """
        Get the appropriate shell-specific prompt with detailed capabilities.

        Returns:
            str: Shell-specific prompt with capabilities.
        """
        shell_info = platform_utils.detect_shell()
        if not shell_info:
            # Default to a generic prompt if shell detection fails
            return "Use standard shell syntax for commands."

        shell_name, shell_version, capabilities = shell_info

        # Check for platform-specific shell overrides first
        current_platform = (
            "windows"
            if platform_utils.is_windows()
            else "macos"
            if platform_utils.is_macos()
            else "linux"
        )
        if (
            current_platform in self.platform_shell_overrides
            and shell_name in self.platform_shell_overrides[current_platform]
        ):
            prompt = self.platform_shell_overrides[current_platform][shell_name]
        # Fall back to standard shell prompts
        elif shell_name in self.shell_prompts:
            prompt = self.shell_prompts[shell_name]
        else:
            prompt = "Use standard shell syntax for commands."

        # Add shell version information
        prompt += f"\nDetected shell version: {shell_version}\n"

        # Add shell capabilities information
        prompt += "\nShell capabilities:\n"

        # Add key capabilities with explanations
        capability_explanations = {
            "supports_redirection": "Supports input/output redirection",
            "supports_pipes": "Supports command piping",
            "filename_completion": "Supports filename tab completion",
            "command_aliases": "Supports command aliases/shortcuts",
            "array_support": "Supports array data structures",
            "process_substitution": "Supports process substitution",
            "supports_unicode": "Supports Unicode characters",
            "multiline_commands": "Supports multi-line commands",
            "command_history": "Maintains command history",
            "command_editing": "Supports command-line editing",
        }

        # Add shell-specific capability explanations
        if shell_name in ["powershell", "pwsh"]:
            capability_explanations.update(
                {
                    "object_pipeline": "Supports object-based pipeline",
                    "type_system": "Has strong type system",
                }
            )

        # Add capabilities to the prompt
        for capability, explanation in capability_explanations.items():
            if capability in capabilities:
                prompt += (
                    f"- {explanation}: {'Yes' if capabilities[capability] else 'No'}\n"
                )

        # Add shell-specific command guidelines
        prompt += "\nCommand guidelines for this shell:\n"

        if shell_name in ["powershell", "pwsh"]:
            prompt += """
- Use PowerShell cmdlets (verb-noun format like Get-ChildItem instead of ls)
- Use object-oriented pipeline with Select-Object, Where-Object, etc.
- Use PowerShell parameter syntax with dash prefix (-Path, -Filter, etc.)
- Use $variables for variable references
- For file paths, use backslashes or ensure forward slashes are handled properly
- Use PowerShell comparison operators (-eq, -lt, -gt) instead of ==, <, >
"""
        elif shell_name == "cmd":
            prompt += """
- Use basic CMD commands and batch syntax
- Use %variables% for environment variables
- Avoid advanced constructs not supported in CMD
- Always use backslashes for file paths
- Use built-in commands like dir, type, findstr instead of Unix equivalents
- Remember that CMD has limited scripting capabilities
"""
        elif shell_name == "bash":
            if platform_utils.is_windows():
                prompt += """
- Use standard Unix commands in Git Bash on Windows
- Remember that Git Bash is running on Windows, but uses Unix commands
- Use $variables and ${complex_variables} for variable references
- Always use forward slashes for file paths, not backslashes
- Use bash arrays when needed with syntax like array=("item1" "item2")
- Do NOT use PowerShell cmdlets or CMD commands
- For Windows paths, use /c/Users instead of C:\\Users
"""
            else:
                prompt += """
- Use standard Unix commands
- Leverage bash-specific features like process substitution when needed
- Use $variables and ${complex_variables} for variable references
- Always use forward slashes for file paths
- Use bash arrays when needed with syntax like array=("item1" "item2")
- Remember that bash supports advanced scripting features
"""
        elif shell_name == "zsh":
            prompt += """
- Use standard Unix commands with zsh enhancements
- Take advantage of zsh's advanced globbing features
- Use $variables and ${complex_variables} for variable references
- Always use forward slashes for file paths
- Remember that zsh has enhanced array handling and scripting features
"""
        elif shell_name == "fish":
            prompt += """
- Use standard Unix commands with fish syntax
- Use $variables for variable references (no $ for variable assignment)
- Always use forward slashes for file paths
- Remember that fish uses different scripting syntax than bash/zsh
- Use fish's built-in functions for common operations
"""

        return prompt

    def build_system_context(
        self, include_platform_info: bool = True
    ) -> Dict[str, Any]:
        """
        Build a system context dictionary with enhanced platform and shell information.

        Args:
            include_platform_info (bool): Whether to include platform information.

        Returns:
            Dict[str, Any]: System context dictionary.
        """
        context = {}

        if include_platform_info:
            # Get platform information
            platform_info = platform_utils.get_platform_info()
            context.update(platform_info)

            # Add terminal capabilities
            context["supports_ansi_colors"] = platform_utils.supports_ansi_colors()
            context["terminal_size"] = platform_utils.get_terminal_size()

            # Add enhanced shell information
            shell_info = platform_utils.detect_shell()
            if shell_info:
                shell_name, shell_version, capabilities = shell_info
                context["shell_name"] = shell_name
                context["shell_version"] = shell_version
                context["shell_capabilities"] = capabilities

        return context

    def build_enhanced_system_prompt(self):
        """
        Build an enhanced system prompt with detailed examples and guidelines.

        Returns:
            str: Enhanced system prompt text
        """
        return """
        You are CommandRex, an expert in translating natural language to "
        "terminal commands.
        Your task is to convert user requests into the most appropriate command "
        "for their system.

        For each request, you should:
        1. Determine the user's intent
        2. Select the most appropriate command(s) for their system
        3. Format the command correctly
        4. Provide a clear explanation
        5. Assess the safety of the command
        6. Break down the command components
        7. Suggest alternatives if appropriate

        IMPORTANT GUIDELINES:
        1. Prioritize the most idiomatic command for the user's platform
        2. Include necessary flags but prefer the most common/standard options
        3. Protect users from destructive operations with warnings
        4. Explain command components thoroughly
        5. Provide alternatives when appropriate

        COMMAND ACCURACY GUIDELINES:
        - For file operations, check if paths need quotes
        - For filters (grep/find), ensure proper regex escaping
        - For piped commands, ensure compatibility between components
        - For Windows PowerShell, use proper cmdlet syntax
        - Use platform-specific path separators consistently

        RESPONSE FORMAT REQUIREMENTS:
        You MUST respond in valid JSON format with this EXACT structure:
        {
          "command": "the exact command to execute",
          "explanation": "explanation of what the command does",
          "safety_assessment": {
            "is_safe": true or false,
            "concerns": ["specific", "potential", "issues"],
            "risk_level": "none" or "low" or "medium" or "high"
          },
          "components": [
            {"part": "specific command part", "description": "what this part does"}
          ],
          "is_dangerous": true or false,
          "alternatives": ["alternative command 1", "alternative command 2"]
        }
        """

    def _get_platform_examples(self):
        """
        Get platform-specific examples for the current platform.

        Returns:
            str: Platform-specific examples
        """
        # Check if we're in Git Bash on Windows
        shell_info = platform_utils.detect_shell()
        if platform_utils.is_windows() and shell_info and shell_info[0] == "bash":
            return self._get_git_bash_examples()

        # Standard platform detection
        if platform_utils.is_windows():
            shell_info = platform_utils.detect_shell()
            if shell_info and shell_info[0] == "powershell":
                return self._get_powershell_examples()
            else:
                return self._get_cmd_examples()
        elif platform_utils.is_macos():
            return self._get_macos_examples()
        elif platform_utils.is_linux():
            return self._get_linux_examples()
        else:
            return self._get_generic_examples()

    def _get_git_bash_examples(self):
        """Get Git Bash-specific command examples."""
        return """
        EXAMPLE TRANSLATIONS FOR GIT BASH ON WINDOWS:

        [User: "list files in current directory"]
        {"command": "ls -la"}

        [User: "find large files in my downloads folder"]
        {"command": "find ~/Downloads -type f -size +10M -exec ls -lh {} \\; "
        "| sort -rh"}

        [User: "show processes using the most memory"]
        {"command": "ps aux --sort=-%mem | head -n 10"}

        [User: "create a backup of my documents folder"]
        {"command": "tar -czf ~/Documents_Backup_$(date +%Y%m%d).tar.gz ~/Documents"}

        [User: "find all text files containing the word 'important'"]
        {"command": "grep -r --include=\"*.txt\" \"important\" ."}

        [User: "show me disk space usage"]
        {"command": "df -h"}

        [User: "check system load average"]
        {"command": "uptime"}
        """

    def _get_powershell_examples(self):
        """Get PowerShell-specific command examples."""
        return """
        EXAMPLE TRANSLATIONS FOR POWERSHELL:

        [User: "find large files in my downloads folder"]
        {"command": "Get-ChildItem -Path \"$HOME\\Downloads\" -Recurse | "
        "Where-Object {$_.Length -gt 10MB} | Sort-Object -Property Length "
        "-Descending"}

        [User: "show processes using the most memory"]
        {"command": "Get-Process | Sort-Object -Property WorkingSet -Descending | "
        "Select-Object -First 10 Name, Id, WorkingSet"}

        [User: "create a backup of my documents folder"]
        {"command": "Compress-Archive -Path \"$HOME\\Documents\" "
        "-DestinationPath \"$HOME\\Documents_Backup_$(Get-Date -Format "
        "'yyyyMMdd').zip\""}

        [User: "find all text files containing the word 'important'"]
        {"command": "Get-ChildItem -Path . -Filter *.txt -Recurse | "
        "Select-String -Pattern \"important\" | Group-Object Path | "
        "Select-Object Name"}

        [User: "show me disk space usage"]
        {"command": "Get-PSDrive -PSProvider FileSystem | Format-Table "
        "-Property Name, Used, Free"}
        """

    def _get_cmd_examples(self):
        """Get Windows CMD-specific command examples."""
        return """
        EXAMPLE TRANSLATIONS FOR WINDOWS CMD:

        [User: "find large files in my downloads folder"]
        {"command": "dir \"%USERPROFILE%\\Downloads\" /s /b /a-d | findstr /R "
        "\".\" > temp.txt && for /F \"tokens=*\" %i in ('type temp.txt') do "
        "@echo %~zi %i | findstr /R \"[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]\" "
        "&& del temp.txt"}

        [User: "show processes using the most memory"]
        {"command": "tasklist /v /fi \"memusage gt 10000\" /sort:memusage"}

        [User: "create a backup of my documents folder"]
        {"command": "xcopy \"%USERPROFILE%\\Documents\" "
        "\"%USERPROFILE%\\Documents_Backup_%date:~10,4%%date:~4,2%%date:~7,2%\" "
        "/E /I /H"}

        [User: "find all text files containing the word 'important'"]
        {"command": "findstr /s /i /m \"important\" *.txt"}

        [User: "show me disk space usage"]
        {"command": "wmic logicaldisk get deviceid, size, freespace"}
        """

    def _get_macos_examples(self):
        """Get macOS-specific command examples."""
        return """
        EXAMPLE TRANSLATIONS FOR MACOS:

        [User: "find large files in my downloads folder"]
        {"command": "find ~/Downloads -type f -size +10M -exec ls -lh {} \\; "
        "| sort -rh"}

        [User: "show processes using the most memory"]
        {"command": "ps aux --sort=-%mem | head -n 10"}

        [User: "create a backup of my documents folder"]
        {"command": "tar -czf ~/Documents_Backup_$(date +%Y%m%d).tar.gz ~/Documents"}

        [User: "find all text files containing the word 'important'"]
        {"command": "grep -r --include=\"*.txt\" \"important\" ."}

        [User: "show me disk space usage"]
        {"command": "df -h"}
        """

    def _get_linux_examples(self):
        """Get Linux-specific command examples."""
        return """
        EXAMPLE TRANSLATIONS FOR LINUX:

        [User: "find large files in my downloads folder"]
        {"command": "find ~/Downloads -type f -size +10M -exec ls -lh {} \\; "
        "| sort -rh"}

        [User: "show processes using the most memory"]
        {"command": "ps aux --sort=-%mem | head -n 10"}

        [User: "create a backup of my documents folder"]
        {"command": "tar -czf ~/Documents_Backup_$(date +%Y%m%d).tar.gz ~/Documents"}

        [User: "find all text files containing the word 'important'"]
        {"command": "grep -r --include=\"*.txt\" \"important\" ."}

        [User: "show me disk space usage"]
        {"command": "df -h"}

        [User: "check system load average"]
        {"command": "uptime"}
        """

    def _get_generic_examples(self):
        """Get generic command examples for unknown platforms."""
        return """
        EXAMPLE TRANSLATIONS:

        [User: "find large files in my downloads folder"]
        {"command": "find ~/Downloads -type f -size +10M -exec ls -lh {} \\; "
        "| sort -rh"}

        [User: "show processes using the most memory"]
        {"command": "ps aux --sort=-%mem | head -n 10"}

        [User: "create a backup of my documents folder"]
        {"command": "tar -czf ~/Documents_Backup_$(date +%Y%m%d).tar.gz ~/Documents"}
        """

    def _get_shell_specific_examples(self, shell_name: str) -> str:
        """
        Get command examples specific to the detected shell.

        Args:
            shell_name (str): Name of the shell

        Returns:
            str: Shell-specific command examples
        """
        # Special case for Git Bash on Windows
        if shell_name == "bash" and platform_utils.is_windows():
            return """
            [Task: "List files with details"]
            {"command": "ls -la"}

            [Task: "Find text in files"]
            {"command": "grep -r 'searchtext' ."}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "ps aux --sort=-%mem | head -10"}

            [Task: "Create a directory"]
            {"command": "mkdir -p NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "find . -name '*.txt' -exec cp {} ~/Backup \\;"}

            [Task: "List files in current directory"]
            {"command": "ls -la"}
            """

        if shell_name in ["powershell", "pwsh"]:
            return """
            [Task: "List files with details"]
            {"command": "Get-ChildItem | Format-Table -Property Name, Length, "
            "LastWriteTime"}

            [Task: "Find text in files"]
            {"command": "Get-ChildItem -Recurse | Select-String -Pattern 'searchtext'"}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "Get-Process | Sort-Object -Property WorkingSet "
            "-Descending | Select-Object -First 10 Name, Id, WorkingSet"}

            [Task: "Create a directory"]
            {"command": "New-Item -ItemType Directory -Path 'NewFolder'"}

            [Task: "Copy files with specific extension"]
            {"command": "Get-ChildItem -Path . -Filter *.txt | Copy-Item "
            "-Destination C:\\Backup"}
            """
        elif shell_name == "cmd":
            return """
            [Task: "List files with details"]
            {"command": "dir /a"}

            [Task: "Find text in files"]
            {"command": "findstr /s /i 'searchtext' *.*"}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "tasklist /v /fi 'memusage gt 1000' /sort:memusage"}

            [Task: "Create a directory"]
            {"command": "mkdir NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "for %i in (*.txt) do copy %i C:\\Backup"}
            """
        elif shell_name == "bash":
            return """
            [Task: "List files with details"]
            {"command": "ls -la"}

            [Task: "Find text in files"]
            {"command": "grep -r 'searchtext' ."}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "ps aux --sort=-%mem | head -10"}

            [Task: "Create a directory"]
            {"command": "mkdir -p NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "find . -name '*.txt' -exec cp {} ~/Backup \\;"}
            """
        elif shell_name == "zsh":
            return """
            [Task: "List files with details"]
            {"command": "ls -la"}

            [Task: "Find text in files"]
            {"command": "grep -r 'searchtext' ."}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "ps aux --sort=-%mem | head -10"}

            [Task: "Create a directory"]
            {"command": "mkdir -p NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "cp *.txt ~/Backup"}
            """
        elif shell_name == "fish":
            return """
            [Task: "List files with details"]
            {"command": "ls -la"}

            [Task: "Find text in files"]
            {"command": "grep -r 'searchtext' ."}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "ps aux --sort=-%mem | head -10"}

            [Task: "Create a directory"]
            {"command": "mkdir -p NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "for file in *.txt; cp $file ~/Backup; end"}
            """
        else:
            # Default to generic Unix examples
            return """
            [Task: "List files with details"]
            {"command": "ls -la"}

            [Task: "Find text in files"]
            {"command": "grep -r 'searchtext' ."}

            [Task: "Get running processes sorted by memory usage"]
            {"command": "ps aux --sort=-%mem | head -10"}

            [Task: "Create a directory"]
            {"command": "mkdir -p NewFolder"}

            [Task: "Copy files with specific extension"]
            {"command": "find . -name '*.txt' -exec cp {} ~/Backup \\;"}
            """

    def build_translation_prompt(
        self,
        user_request: str,
        command_history: Optional[List[str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Build a complete prompt for command translation with enhanced shell awareness.

        Args:
            user_request (str): The user's natural language request.
            command_history (Optional[List[str]]): Previous commands for context.
            user_preferences (Optional[Dict[str, Any]]): User preferences.

        Returns:
            List[Dict[str, str]]: List of message dictionaries for the OpenAI API.
        """
        messages = []

        # System prompt
        system_prompt = self.base_system_prompt + "\n\n" + self.safety_prompt

        # Add platform and shell information
        system_prompt += "\n\n" + self._get_platform_prompt()
        system_prompt += "\n" + self._get_shell_prompt()

        # Add platform-specific examples
        system_prompt += "\n\n" + self._get_platform_examples()

        # Add command adaptation instruction
        system_prompt += (
            "\n\nIMPORTANT: Always adapt commands to the detected shell environment. "
        )
        system_prompt += (
            "Use shell-specific syntax and commands that are "
            "optimal for the user's shell."
        )

        # Add strict environment constraints to prevent incorrect commands
        shell_info_for_rules = platform_utils.detect_shell()
        if shell_info_for_rules:
            detected_shell = (shell_info_for_rules[0] or "").lower()
            os_name = platform_utils.get_platform_info().get("os_name", "Unknown")
            rules = self.STRICT_ENVIRONMENT_RULES.get(detected_shell)
            if rules:
                forbidden = ", ".join(rules.get("forbidden_commands", []))
                path_sep = rules.get("required_syntax", {}).get("path_separator", "/")
                wrong_sep = rules.get("wrong_separator", "\\")
                # Keep lines under E501 by splitting strings
                system_prompt += "\n\nCRITICAL ENVIRONMENT CONSTRAINTS:\n"
                system_prompt += f"- Detected Shell: {detected_shell}\n"
                system_prompt += f"- Detected OS: {os_name}\n"
                system_prompt += f"- FORBIDDEN commands: {forbidden}\n"
                system_prompt += (
                    f"- REQUIRED path separator: '{path_sep}' "
                    f"(never use '{wrong_sep}')\n"
                )
                system_prompt += (
                    "- NEVER mix syntax from other shells. Do not use Unix commands "
                    "in Windows shells or Windows commands in Unix shells.\n"
                )
                system_prompt += (
                    "- If a command is not available in this environment, choose a "
                    "functionally equivalent command that IS available.\n"
                )

        # Special case for Git Bash on Windows
        shell_info = platform_utils.detect_shell()
        if platform_utils.is_windows() and shell_info and shell_info[0] == "bash":
            system_prompt += "\n\nCRITICAL: You are in Git Bash on Windows. "
            system_prompt += (
                "You MUST use Unix/Bash commands like 'ls', NOT "
                "Windows commands like 'Get-ChildItem' or 'dir'. "
            )
            system_prompt += "Always use forward slashes for paths. "
            system_prompt += (
                "Git Bash is a Unix-like environment on Windows, so use Unix commands."
            )

        messages.append({"role": "system", "content": system_prompt})

        # Add system context
        system_context = self.build_system_context()
        messages.append(
            {
                "role": "system",
                "content": f"System information: "
                f"{json.dumps(system_context, indent=2)}",
            }
        )

        # Add shell-specific examples based on detected shell
        shell_info = platform_utils.detect_shell()
        if shell_info:
            shell_name, shell_version, capabilities = shell_info
            shell_examples = self._get_shell_specific_examples(shell_name)
            if shell_examples:
                messages.append(
                    {
                        "role": "system",
                        "content": f"Examples for {shell_name} shell:\n"
                        f"{shell_examples}",
                    }
                )

        # Add command history for context if available
        if command_history and len(command_history) > 0:
            history_prompt = "Recent command history:\n"
            for i, cmd in enumerate(command_history[-5:]):  # Last 5 commands
                history_prompt += f"{i + 1}. {cmd}\n"

            messages.append({"role": "system", "content": history_prompt})

        # Add user preferences if available
        if user_preferences:
            pref_prompt = "User preferences:\n"
            for key, value in user_preferences.items():
                pref_prompt += f"- {key}: {value}\n"

            messages.append({"role": "system", "content": pref_prompt})

        # Add the user's request
        messages.append({"role": "user", "content": user_request})

        return messages

    def build_explanation_prompt(self, command: str) -> List[Dict[str, str]]:
        """
        Build a prompt for explaining a command.

        Args:
            command (str): The command to explain.

        Returns:
            List[Dict[str, str]]: List of message dictionaries for the OpenAI API.
        """
        system_prompt = """
        You are CommandRex, an expert in explaining terminal commands.
        Your task is to explain the given command in a clear, educational way.
        Break down each component and explain what it does.

        EXPLANATION GUIDELINES:
        1. Start with a high-level overview of what the command accomplishes
        2. Break down each component (command, flags, arguments, etc.)
        3. Explain how the components work together
        4. Mention any potential pitfalls or common mistakes
        5. Suggest related commands or variations

        COMPONENT BREAKDOWN GUIDELINES:
        - For each flag, explain its specific purpose
        - For arguments, explain the expected format and impact
        - For pipes or redirections, explain how data flows
        - For complex syntax, explain the pattern and why it works

        RESPONSE FORMAT REQUIREMENTS:
        You MUST respond in valid JSON format with this EXACT structure:
        {
          "explanation": "overall explanation of the command",
          "components": [
            {"part": "specific command part", "description": "what this part does"}
          ],
          "examples": ["example usage 1", "example usage 2"],
          "related_commands": ["related1", "related2"]
        }

        EXAMPLE EXPLANATIONS:

        [Command: "find . -name "*.txt" -type f -size +1M"]
        {
          "explanation": "This command searches for text files larger than "
          "1 megabyte in the current directory and all subdirectories.",
          "components": [
            {"part": "find", "description": "The command that searches for files "
            "in a directory hierarchy"},
            {"part": ".", "description": "The starting directory for the search "
            "(current directory)"},
            {"part": "-name \"*.txt\"", "description": "Matches files with names "
            "ending in .txt"},
            {"part": "-type f", "description": "Restricts the search to regular "
            "files (not directories or other special files)"},
            {"part": "-size +1M", "description": "Matches files larger than 1 megabyte"}
          ],
          "examples": [
            "find /home/user -name \"*.log\" -type f -size +10M",
            "find Documents -name \"report*.txt\" -type f -mtime -7"
          ],
          "related_commands": ["grep", "locate", "ls", "du"]
        }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Explain this command: {command}"},
        ]

        return messages

    def build_safety_assessment_prompt(self, command: str) -> List[Dict[str, str]]:
        """
        Build a prompt for assessing command safety.

        Args:
            command (str): The command to assess.

        Returns:
            List[Dict[str, str]]: List of message dictionaries for the OpenAI API.
        """
        system_prompt = """
        You are CommandRex, an expert in terminal command safety.
        Your task is to assess the safety of the given command.
        Identify any potentially dangerous operations, such as file deletion,
        system modifications, or network operations.

        SAFETY ASSESSMENT GUIDELINES:
        1. Carefully analyze the command for destructive operations
        2. Consider the scope of impact (single file vs. entire system)
        3. Identify potential unintended consequences
        4. Assess the reversibility of the operation
        5. Consider security implications

        RISK CATEGORIES TO CHECK:
        - Data loss: Commands that delete, overwrite, or modify files
        - System modification: Changes to system settings or configuration
        - Security risks: Exposure of sensitive data or security weaknesses
        - Resource consumption: Commands that might consume excessive resources
        - Network impact: Operations affecting network services or connections

        RESPONSE FORMAT REQUIREMENTS:
        You MUST respond in valid JSON format with this EXACT structure:
        {
          "is_safe": true or false,
          "risk_level": "none" or "low" or "medium" or "high",
          "concerns": ["specific concern 1", "specific concern 2"],
          "recommendations": ["recommendation 1", "recommendation 2"],
          "safer_alternatives": ["safer alternative 1", "safer alternative 2"]
        }

        EXAMPLE ASSESSMENTS:

        [Command: "rm -rf /"]
        {
          "is_safe": false,
          "risk_level": "high",
          "concerns": [
            "This command attempts to recursively delete all files from the "
            "root directory",
            "Would cause catastrophic data loss and system failure",
            "Requires elevated privileges but would be destructive if run with sudo"
          ],
          "recommendations": [
            "Never run this command under any circumstances",
            "Use targeted removal commands with specific paths instead"
          ],
          "safer_alternatives": [
            "rm -rf ./specific_directory",
            "find ./directory -name 'pattern' -delete"
          ]
        }

        [Command: "ls -la"]
        {
          "is_safe": true,
          "risk_level": "none",
          "concerns": [],
          "recommendations": [],
          "safer_alternatives": []
        }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Assess the safety of this command: {command}",
            },
        ]

        return messages
