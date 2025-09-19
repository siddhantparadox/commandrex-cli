"""
Platform detection and utilities for CommandRex.

This module provides functions to detect the operating system,
shell environment, and system capabilities to ensure cross-platform
compatibility.
"""

import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def get_platform_info() -> Dict[str, str]:
    """
    Get detailed information about the current platform.

    Returns:
        Dict[str, str]: Dictionary containing platform information.
    """
    # Get basic platform info
    system_name = platform.system()

    # Simplified OS info - just the name without version
    info = {
        "os_name": system_name,
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
    }

    # Add shell information if available
    shell_info = detect_shell()
    if shell_info:
        info["shell_name"] = shell_info[0]
        info["shell_version"] = shell_info[1]

    return info


def is_windows() -> bool:
    """
    Check if the current platform is Windows.

    Returns:
        bool: True if Windows, False otherwise.
    """
    return platform.system().lower() == "windows"


def is_macos() -> bool:
    """
    Check if the current platform is macOS.

    Returns:
        bool: True if macOS, False otherwise.
    """
    return platform.system().lower() == "darwin"


def is_linux() -> bool:
    """
    Check if the current platform is Linux.

    Returns:
        bool: True if Linux, False otherwise.
    """
    return platform.system().lower() == "linux"


def detect_shell() -> Optional[
    Tuple[str, str, Dict[str, Any]]
]:  # pragma: no cover - depends on host shell state
    """
    Enhanced shell detection with multiple fallback mechanisms.

    Returns:
        Optional[Tuple[str, str, Dict[str, Any]]]:
            Tuple of (shell_name, shell_version, shell_capabilities) or None if
            detection fails.
    """
    # Try multiple detection methods in order of reliability
    shell_info = detect_shell_from_environment()
    if shell_info and shell_info[0]:
        shell_name, shell_version = shell_info
        capabilities = get_shell_capabilities(shell_name)
        return shell_name, shell_version, capabilities

    shell_info = detect_shell_from_commands()
    if shell_info and shell_info[0]:
        shell_name, shell_version = shell_info
        capabilities = get_shell_capabilities(shell_name)
        return shell_name, shell_version, capabilities

    shell_info = detect_shell_from_behavior()
    if shell_info and shell_info[0]:
        shell_name, shell_version = shell_info
        capabilities = get_shell_capabilities(shell_name)
        return shell_name, shell_version, capabilities

    # Fallback to best guess
    shell_name, shell_version = determine_best_guess_shell()
    if shell_name:
        capabilities = get_shell_capabilities(shell_name)
        return shell_name, shell_version, capabilities

    return None


def detect_shell_from_environment() -> Optional[
    Tuple[str, str]
]:  # pragma: no cover - depends on environment variables
    """
    Detect shell from environment variables.

    Returns:
        Optional[Tuple[str, str]]: Tuple of (shell_name, shell_version) or None
        if detection fails.
    """
    shell_name = ""
    shell_version = ""

    # On Windows, we need to be more careful about shell detection
    if is_windows():
        # Try to detect the parent process first (most reliable)
        parent_process_info = get_parent_process_info()
        if parent_process_info:
            parent_name, parent_cmd = parent_process_info

            # Check for CMD
            if "cmd.exe" in parent_name.lower():
                shell_name = "cmd"
                shell_version = platform.version()
                return shell_name, shell_version

            # Check for PowerShell
            if "powershell.exe" in parent_name.lower():
                shell_name = "powershell"
                # Try to get PowerShell version
                try:
                    result = subprocess.run(
                        [
                            "powershell",
                            "-Command",
                            "$PSVersionTable.PSVersion.ToString()",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if result.stdout:
                        shell_version = result.stdout.strip()
                except Exception:
                    pass
                return shell_name, shell_version

            # Check for PowerShell Core
            if "pwsh.exe" in parent_name.lower():
                shell_name = "pwsh"
                # Try to get PowerShell version
                try:
                    result = subprocess.run(
                        ["pwsh", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                        capture_output=True,
                        text=True,
                        timeout=1,
                    )
                    if result.stdout:
                        shell_version = result.stdout.strip()
                except Exception:
                    pass
                return shell_name, shell_version

            # Check for Git Bash / MINGW
            if (
                "bash.exe" in parent_name.lower()
                or "git-bash.exe" in parent_name.lower()
            ):
                shell_name = "bash"
                # Try to get Git Bash version
                try:
                    result = subprocess.run(
                        ["bash", "--version"], capture_output=True, text=True, timeout=1
                    )
                    if result.stdout:
                        parts = result.stdout.split("\n")[0].split("version ")
                        if len(parts) > 1:
                            shell_version = parts[1].split()[0]
                except Exception:
                    pass
                return shell_name, shell_version

        # If parent process detection failed, try environment variables

        # Check for CMD-specific environment variables (higher priority)
        cmd_indicators = [
            "PROMPT" in os.environ,
            "ComSpec" in os.environ
            and "cmd.exe" in os.environ.get("ComSpec", "").lower(),
            "CMDEXTVERSION" in os.environ,
            # Check if we're NOT in PowerShell
            not any(ps_var for ps_var in os.environ.keys() if ps_var.startswith("PS")),
        ]

        # If multiple CMD indicators are true, we're likely in CMD
        if sum(cmd_indicators) >= 2:
            shell_name = "cmd"
            shell_version = platform.version()
            return shell_name, shell_version

        # Check for Git Bash / MINGW environment
        if "MSYSTEM" in os.environ and "MINGW" in os.environ.get("MSYSTEM", ""):
            shell_name = "bash"
            # Try to get Git Bash version
            try:
                result = subprocess.run(
                    ["bash", "--version"], capture_output=True, text=True, timeout=1
                )
                if result.stdout:
                    parts = result.stdout.split("\n")[0].split("version ")
                    if len(parts) > 1:
                        shell_version = parts[1].split()[0]
            except Exception:
                pass
            return shell_name, shell_version

        # Check for PowerShell-specific environment variables
        if any(ps_var for ps_var in os.environ.keys() if ps_var.startswith("PS")):
            # Determine if it's PowerShell Core (pwsh) or Windows PowerShell
            if "PSCore" in os.environ.get("PSModulePath", "") or os.environ.get(
                "POWERSHELL_DISTRIBUTION_CHANNEL"
            ):
                shell_name = "pwsh"
            else:
                shell_name = "powershell"

            # Try to get PowerShell version
            try:
                ps_exec = "pwsh" if shell_name == "pwsh" else "powershell"
                result = subprocess.run(
                    [ps_exec, "-Command", "$PSVersionTable.PSVersion.ToString()"],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if result.stdout:
                    shell_version = result.stdout.strip()
            except Exception:
                pass

            return shell_name, shell_version

        # Check for WSL environment
        if "WSL_DISTRO_NAME" in os.environ:
            # We're in WSL, likely bash
            shell_name = "bash"
            shell_version = os.environ.get("BASH_VERSION", "").split()[0]
            return shell_name, shell_version
    else:
        # Unix-like systems
        # Check for common shell environment variables
        if "BASH_VERSION" in os.environ:
            shell_name = "bash"
            shell_version = os.environ.get("BASH_VERSION", "").split()[0]
        elif "ZSH_VERSION" in os.environ:
            shell_name = "zsh"
            shell_version = os.environ.get("ZSH_VERSION", "")
        elif "FISH_VERSION" in os.environ:
            shell_name = "fish"
            shell_version = os.environ.get("FISH_VERSION", "")

    # If shell wasn't detected yet, fall back to standard detection
    if not shell_name:
        # Try to get from environment variables
        shell_path = os.environ.get("SHELL") or os.environ.get("COMSPEC")

        if not shell_path and is_windows():
            # On Windows, default to cmd.exe if not found
            shell_path = "cmd.exe"

        if not shell_path:
            return None

        shell_name = os.path.basename(shell_path).lower()

        # Extract shell name without extension
        if "." in shell_name:
            shell_name = shell_name.split(".")[0]

    # If we have a shell name but no version, try to get the version
    if shell_name and not shell_version:
        shell_version = get_shell_version(shell_name)

    return shell_name, shell_version


def get_parent_process_info() -> Optional[
    Tuple[str, str]
]:  # pragma: no cover - inspects host process tree
    """
    Get information about the parent process.

    Returns:
        Optional[Tuple[str, str]]: Tuple of (process_name, command_line) or None
        if detection fails.
    """
    try:
        if is_windows():
            # Use PowerShell to get parent process info
            # This is more reliable than using Python's psutil on Windows
            cmd = [
                "powershell",
                "-Command",
                (
                    '$parent = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID")'
                    ".ParentProcessId; "
                )
                + "$parentProc = Get-Process -Id $parent; "
                + "Write-Output ($parentProc.ProcessName + '|' + $parentProc.Path)",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)

            if result.returncode == 0 and result.stdout:
                parts = result.stdout.strip().split("|")
                if len(parts) >= 2:
                    return parts[0], parts[1]
                elif len(parts) == 1:
                    return parts[0], ""
        else:
            # On Unix systems, we could use psutil if available
            # For now, return None as this is primarily for Windows
            pass
    except Exception:
        # If process detection fails, return None
        pass

    return None


def detect_shell_from_commands() -> Optional[
    Tuple[str, str]
]:  # pragma: no cover - runs platform commands
    """
    Detect shell by running shell-specific commands.

    Returns:
        Optional[Tuple[str, str]]: Tuple of (shell_name, shell_version) or None
        if detection fails.
    """
    # Try to detect shell by running shell-specific commands
    # Order matters - try CMD first on Windows, then Git Bash, then PowerShell
    shell_commands = {}

    if is_windows():
        shell_commands = {
            "cmd": ["cmd", "/c", "echo %COMSPEC%"],  # CMD (highest priority)
            "bash": ["bash", "--version"],  # Git Bash
            "powershell": [
                "powershell",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ],
            "pwsh": ["pwsh", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        }
    else:
        shell_commands = {
            "bash": ["bash", "--version"],
            "zsh": ["zsh", "--version"],
            "fish": ["fish", "--version"],
        }

    for shell_name, command in shell_commands.items():
        try:
            # Skip non-Windows shells on Windows except for bash (Git Bash)
            if is_windows() and shell_name not in ["powershell", "pwsh", "cmd", "bash"]:
                continue

            # Skip Windows-only shells on non-Windows
            if not is_windows() and shell_name in ["powershell", "pwsh", "cmd"]:
                continue

            result = subprocess.run(command, capture_output=True, text=True, timeout=1)

            if result.returncode == 0 and result.stdout:
                # Command succeeded, this shell is available
                shell_version = parse_shell_version(shell_name, result.stdout)
                return shell_name, shell_version
        except (subprocess.SubprocessError, OSError):
            # Command failed, try next shell
            continue

    return None


def detect_shell_from_behavior() -> Optional[
    Tuple[str, str]
]:  # pragma: no cover - heuristic OS interactions
    """
    Test shell-specific behavior to determine the active shell.

    Returns:
        Optional[Tuple[str, str]]: Tuple of (shell_name, shell_version) or None
        if detection fails.
    """
    import re

    # Define shell-specific behaviors to test
    # Order matters for Windows - check CMD first, then Git Bash, then PowerShell
    shell_behaviors = {}

    if is_windows():
        shell_behaviors = {
            "cmd": [
                {"test": "echo %COMSPEC%", "pattern": r"cmd\.exe"},
                {"test": "echo %OS%", "pattern": r"Windows"},
                {"test": "echo %CMDEXTVERSION%", "pattern": r"\d+"},
            ],
            "bash": [
                {
                    "test": "echo $MSYSTEM",
                    "pattern": r"MINGW|MSYS",
                },  # Git Bash specific
                {"test": "echo $BASH_VERSION", "pattern": r"\d+\.\d+"},
            ],
            "powershell": [
                {
                    "test": "$PSVersionTable.PSVersion.ToString()",
                    "pattern": r"\d+\.\d+",
                },
                {"test": "$Host.Name", "pattern": r"ConsoleHost|ISE Host"},
            ],
            "pwsh": [
                {
                    "test": "$PSVersionTable.PSVersion.ToString()",
                    "pattern": r"\d+\.\d+",
                },
                {"test": "$Host.Name", "pattern": r"ConsoleHost|ISE Host"},
            ],
        }
    else:
        shell_behaviors = {
            "bash": [
                {"test": "echo $BASH_VERSION", "pattern": r"\d+\.\d+"},
                {"test": "echo $BASHPID", "pattern": r"\d+"},
            ],
            "zsh": [
                {"test": "echo $ZSH_VERSION", "pattern": r"\d+\.\d+"},
                {"test": "echo $zsh_eval_context", "pattern": r".+"},
            ],
            "fish": [
                {"test": "echo $FISH_VERSION", "pattern": r"\d+\.\d+"},
                {"test": "echo $fish_pid", "pattern": r"\d+"},
            ],
        }

    results = {}

    for shell, tests in shell_behaviors.items():
        # Skip non-Windows shells on Windows except for bash (which could be Git Bash)
        if is_windows() and shell not in ["powershell", "pwsh", "cmd", "bash"]:
            continue

        # Skip Windows-only shells on non-Windows
        if not is_windows() and shell in ["powershell", "pwsh", "cmd"]:
            continue

        success_count = 0
        for test in tests:
            command = test["test"]
            pattern = test["pattern"]

            try:
                if shell in ["powershell", "pwsh"] and is_windows():
                    cmd = ["powershell", "-Command", command]
                elif shell == "cmd" and is_windows():
                    cmd = ["cmd", "/c", command]
                else:
                    cmd = [shell, "-c", command]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)

                if result.returncode == 0 and re.search(pattern, result.stdout):
                    success_count += 1
            except Exception:
                pass

        if success_count > 0:
            results[shell] = success_count

    if results:
        # Get the shell with the most successful tests
        most_likely_shell = max(results.items(), key=lambda x: x[1])[0]
        shell_version = get_shell_version(most_likely_shell)
        return most_likely_shell, shell_version

    return None


def determine_best_guess_shell() -> Tuple[
    str, str
]:  # pragma: no cover - heuristic fallback
    """
    Make a best guess about the shell if other detection methods fail.

    Returns:
        Tuple[str, str]: Tuple of (shell_name, shell_version)
    """
    if is_windows():
        # On Windows, default to PowerShell for modern systems, cmd for older ones
        try:
            # Check if sys.getwindowsversion is available (Windows only)
            if hasattr(sys, "getwindowsversion"):
                version = sys.getwindowsversion()
                # Windows 10 and later
                if version.major >= 10:
                    return "powershell", get_shell_version("powershell")
                else:
                    return "cmd", platform.version()
            else:
                # Fallback when getwindowsversion is not available
                return "powershell", get_shell_version("powershell")
        except Exception:
            return "cmd", platform.version()
    elif is_macos():
        # macOS default shell is zsh since Catalina, bash before that
        try:
            # Check macOS version
            mac_version = platform.mac_ver()[0]
            if (
                mac_version
                and float(mac_version.split(".")[0] + "." + mac_version.split(".")[1])
                >= 10.15
            ):
                return "zsh", get_shell_version("zsh")
            else:
                return "bash", get_shell_version("bash")
        except Exception:
            return "bash", get_shell_version("bash")
    else:
        # Linux default is usually bash
        return "bash", get_shell_version("bash")


def get_shell_version(
    shell_name: str,
) -> str:  # pragma: no cover - invokes external commands
    """
    Get the version of a specific shell.

    Args:
        shell_name (str): Name of the shell

    Returns:
        str: Shell version or empty string if detection fails
    """
    try:
        if shell_name == "bash":
            result = subprocess.run(
                ["bash", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.stdout:
                # Extract version from output like "GNU bash, version 5.1.16"
                parts = result.stdout.split("\n")[0].split("version ")
                if len(parts) > 1:
                    return parts[1].split()[0]

        elif shell_name == "zsh":
            result = subprocess.run(
                ["zsh", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.stdout:
                # Extract version from output like "zsh 5.8"
                parts = result.stdout.split()
                if len(parts) > 1:
                    return parts[1]

        elif shell_name in ("powershell", "pwsh"):
            # Use the appropriate PowerShell executable
            ps_exec = "pwsh" if shell_name == "pwsh" else "powershell"

            # Try to get PowerShell version
            result = subprocess.run(
                [ps_exec, "-Command", "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout:
                return result.stdout.strip()

        elif shell_name == "cmd":
            # For cmd.exe, try to get the version directly
            try:
                result = subprocess.run(
                    ["cmd", "/c", "ver"], capture_output=True, text=True, timeout=2
                )
                if result.stdout:
                    # Extract version from output like
                    # "Microsoft Windows [Version 10.0.19045.3693]"
                    version_line = result.stdout.strip()
                    if "[Version" in version_line:
                        return version_line.split("[Version")[1].split("]")[0].strip()
                    else:
                        return version_line
            except Exception:
                # Fall back to Windows version if cmd version detection fails
                return platform.version()

        elif shell_name == "fish":
            result = subprocess.run(
                ["fish", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.stdout:
                # Extract version from output like "fish, version 3.1.2"
                parts = result.stdout.split("version ")
                if len(parts) > 1:
                    return parts[1].split()[0]

    except (subprocess.SubprocessError, OSError):
        # If version detection fails, return empty string
        pass

    return ""


def parse_shell_version(
    shell_name: str, version_output: str
) -> str:  # pragma: no cover - formatting helper
    """
    Parse shell version from command output.

    Args:
        shell_name (str): Name of the shell
        version_output (str): Output from version command

    Returns:
        str: Parsed version or empty string if parsing fails
    """
    try:
        if shell_name == "bash":
            # Extract version from output like "GNU bash, version 5.1.16"
            parts = version_output.split("\n")[0].split("version ")
            if len(parts) > 1:
                return parts[1].split()[0]

        elif shell_name == "zsh":
            # Extract version from output like "zsh 5.8"
            parts = version_output.split()
            if len(parts) > 1:
                return parts[1]

        elif shell_name in ("powershell", "pwsh"):
            # PowerShell version is usually just the version string
            return version_output.strip()

        elif shell_name == "cmd":
            # Extract version from output like
            # "Microsoft Windows [Version 10.0.19045.3693]"
            if "[Version" in version_output:
                return version_output.split("[Version")[1].split("]")[0].strip()
            else:
                return version_output.strip()

        elif shell_name == "fish":
            # Extract version from output like "fish, version 3.1.2"
            parts = version_output.split("version ")
            if len(parts) > 1:
                return parts[1].split()[0]

    except Exception:
        # If parsing fails, return empty string
        pass

    return ""


def get_shell_capabilities(
    shell_name: str,
) -> Dict[str, Any]:  # pragma: no cover - depends on platform feature detection
    """
    Detect capabilities of the specified shell.

    Args:
        shell_name (str): Name of the shell

    Returns:
        Dict[str, Any]: Dictionary of shell capabilities
    """
    capabilities = {
        "supports_redirection": True,  # Most shells support basic redirection
        "supports_pipes": True,  # Most shells support pipes
        "filename_completion": False,  # Will be set below
        "command_aliases": False,  # Will be set below
        "array_support": False,  # Will be set below
        "process_substitution": False,  # Will be set below
        "supports_unicode": supports_ansi_colors(),  # If ANSI supported, Unicode too
        "multiline_commands": False,  # Will be set below
        "command_history": False,  # Will be set below
        "command_editing": False,  # Will be set below
    }

    # Set shell-specific capabilities
    if shell_name in ["bash", "zsh", "fish"]:
        capabilities.update(
            {
                "filename_completion": True,
                "command_aliases": True,
                "array_support": True,
                "process_substitution": shell_name
                != "fish",  # fish doesn't support process substitution
                "multiline_commands": True,
                "command_history": True,
                "command_editing": True,
            }
        )

    if shell_name in ["powershell", "pwsh"]:
        capabilities.update(
            {
                "filename_completion": True,
                "command_aliases": True,
                "array_support": True,
                "process_substitution": False,
                "multiline_commands": True,
                "command_history": True,
                "command_editing": True,
                "object_pipeline": True,  # PowerShell specific
                "type_system": True,  # PowerShell specific
            }
        )

    if shell_name == "cmd":
        capabilities.update(
            {
                "filename_completion": True,
                "command_aliases": False,
                "array_support": False,
                "process_substitution": False,
                "multiline_commands": False,
                "command_history": True,
                "command_editing": False,
            }
        )

    # Try to detect advanced capabilities through testing
    try:
        # Example: Test for process substitution in bash
        if shell_name == "bash":
            result = subprocess.run(
                ["bash", "-c", "cat <(echo 'test')"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0 and "test" in result.stdout:
                capabilities["process_substitution"] = True
    except Exception:
        pass

    return capabilities


def get_terminal_size() -> Tuple[
    int, int
]:  # pragma: no cover - relies on real terminal
    """
    Get the current terminal size.

    Returns:
        Tuple[int, int]: (width, height) in characters.
    """
    try:
        columns, lines = shutil.get_terminal_size()
        return columns, lines
    except (AttributeError, OSError):
        # Fallback to default size if detection fails
        return 80, 24


def normalize_path(path: str) -> str:  # pragma: no cover - os-specific behavior
    """
    Normalize a path for the current platform.

    Args:
        path (str): The path to normalize.

    Returns:
        str: Normalized path for the current platform.
    """
    # Expand user directory (~/...)
    if path.startswith("~"):
        path = os.path.expanduser(path)

    # Expand environment variables
    path = os.path.expandvars(path)

    # Normalize path separators and resolve relative paths
    return os.path.normpath(path)


def get_command_prefix() -> str:  # pragma: no cover - user shell dependent
    """
    Get the appropriate command prefix for the current platform.

    Returns:
        str: Command prefix (e.g., "cmd /c" on Windows, "" on Unix).
    """
    if is_windows():
        shell_info = detect_shell()
        if shell_info and shell_info[0] in ("powershell", "pwsh"):
            return "powershell -Command"
        return "cmd /c"
    return ""


def adapt_command_for_shell(
    command: str,
) -> str:  # pragma: no cover - shell specific adjustments
    """
    Adapt a command to work optimally in the detected shell.

    Args:
        command (str): The command to adapt

    Returns:
        str: The adapted command
    """
    shell_info = detect_shell()
    if not shell_info:
        return command

    shell_name, shell_version, capabilities = shell_info

    # PowerShell adaptations
    if shell_name in ["powershell", "pwsh"]:
        # Replace Unix commands with PowerShell equivalents
        command_mapping = {
            r"\bls\b": "Get-ChildItem",
            r"\bcat\b": "Get-Content",
            r"\bgrep\b": "Select-String",
            r"\brm\b": "Remove-Item",
            r"\bcp\b": "Copy-Item",
            r"\bmv\b": "Move-Item",
            r"\bmkdir\b": "New-Item -ItemType Directory -Path",
            r"\becho\b": "Write-Output",
            r"\bfind\b": "Get-ChildItem -Recurse | Where-Object",
        }

        import re

        for unix_cmd, ps_cmd in command_mapping.items():
            command = re.sub(unix_cmd, ps_cmd, command)

        # Fix path separators if they're not in a string
        # This is a simplified approach - a more robust solution would parse the command
        if "/" in command and "\\" not in command:
            command = command.replace("/", "\\")

        # Adapt Unix-style redirections
        command = re.sub(r"(\S+)\s+>\s+(\S+)", r"\1 | Out-File -FilePath \2", command)

    # CMD adaptations
    elif shell_name == "cmd":
        # Replace Unix commands with CMD equivalents
        command_mapping = {
            r"\bls\b": "dir",
            r"\bcat\b": "type",
            r"\bgrep\b": "findstr",
            r"\brm\b": "del",
            r"\bcp\b": "copy",
            r"\bmv\b": "move",
            r"\bmkdir\b": "mkdir",
        }

        import re

        for unix_cmd, cmd_cmd in command_mapping.items():
            command = re.sub(unix_cmd, cmd_cmd, command)

        # Fix path separators
        if "/" in command and "\\" not in command:
            command = command.replace("/", "\\")

    # Bash/Zsh adaptations
    elif shell_name in ["bash", "zsh"]:
        # These shells generally use standard Unix commands
        # Replace Windows commands with Unix equivalents
        command_mapping = {
            r"\bdir\b": "ls",
            r"\btype\b": "cat",
            r"\bfindstr\b": "grep",
            r"\bdel\b": "rm",
            r"\bcopy\b": "cp",
            r"\bmove\b": "mv",
        }

        import re

        for win_cmd, unix_cmd in command_mapping.items():
            command = re.sub(win_cmd, unix_cmd, command)

        # Fix path separators
        if "\\" in command and "/" not in command:
            command = command.replace("\\", "/")

    return command


def find_executable(
    name: str,
) -> Optional[str]:  # pragma: no cover - searches host PATH
    """
    Find the full path to an executable.

    Args:
        name (str): Name of the executable to find.

    Returns:
        Optional[str]: Full path to the executable or None if not found.
    """
    return shutil.which(name)


def get_shell_startup_command() -> List[
    str
]:  # pragma: no cover - depends on shell configuration
    """
    Get the command to start the default shell.

    Returns:
        List[str]: Command list to start the default shell.
    """
    if is_windows():
        shell_info = detect_shell()
        if shell_info and shell_info[0] in ("powershell", "pwsh"):
            return ["powershell"]
        return ["cmd"]

    # For Unix systems, use the SHELL environment variable or fallback to /bin/sh
    shell = os.environ.get("SHELL", "/bin/sh")
    return [shell]


def supports_ansi_colors() -> bool:  # pragma: no cover - terminal capability check
    """
    Check if the terminal supports ANSI colors.

    Returns:
        bool: True if ANSI colors are supported, False otherwise.
    """
    # Windows 10 build 14393 and later support ANSI colors
    if is_windows():
        # Check if running in Windows Terminal, which supports ANSI
        if os.environ.get("WT_SESSION"):
            return True

        # Check Windows version
        try:
            if hasattr(sys, "getwindowsversion"):
                version = sys.getwindowsversion()
                # Windows 10 and later
                if version.major >= 10:
                    return True
        except AttributeError:
            pass

        # Check ANSICON environment variable (third-party ANSI support)
        if os.environ.get("ANSICON"):
            return True

        # Check if running in a terminal that might support colors
        term_env = os.environ.get("TERM")
        if term_env and term_env != "dumb":
            return True

        return False

    # For Unix systems, check TERM environment variable
    term_env = os.environ.get("TERM")
    if term_env and term_env != "dumb":
        return True

    # Check if stdout is a TTY
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
