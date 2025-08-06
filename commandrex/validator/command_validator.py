"""
Environment-aware command validator for CommandRex.

This module enforces strict validation that a generated command matches the
current OS and shell, rejecting commands that are incompatible before they
reach execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from commandrex.executor import platform_utils


@dataclass
class ValidationIssue:
    code: str
    message: str
    detail: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add(
        self, code: str, message: str, detail: Optional[Dict[str, Any]] = None
    ) -> None:
        self.issues.append(
            ValidationIssue(code=code, message=message, detail=detail or {})
        )

    @property
    def reasons(self) -> List[str]:
        return [i.message for i in self.issues]


class CommandValidator:
    """
    Strict environment validator.

    Validations:
      1) Forbidden token checks per shell
      2) Path separator correctness
      3) Shell syntax heuristics (very coarse)
      4) Minimal OS/shell coherence (e.g., Windows-only commands on Unix)
    """

    # Forbidden token lists (as substrings or simple regex starts-with)
    FORBIDDEN_BY_SHELL: Dict[str, Dict[str, List[str]]] = {
        "cmd": {
            "forbidden_tokens": [
                " ls ",
                "grep ",
                " cat ",
                " chmod",
                " chown",
                " find ",
                " which",
                " man ",
                " sudo",
                " tar ",
            ],
            "starts_with": [],
            "wrong_sep": "/",
            "right_sep": "\\",
        },
        "powershell": {
            "forbidden_tokens": [
                " grep ",
                " cat ",
                " sed ",
                " awk ",
                " chmod",
                " chown",
                " sudo",
            ],
            "starts_with": [],
            "wrong_sep": "/",
            "right_sep": "\\",
        },
        "pwsh": {
            "forbidden_tokens": [
                " grep ",
                " cat ",
                " sed ",
                " awk ",
                " chmod",
                " chown",
                " sudo",
            ],
            "starts_with": [],
            "wrong_sep": "/",
            "right_sep": "\\",
        },
        "bash": {
            "forbidden_tokens": [
                " findstr",
                " dir ",
                " type ",
                " cls",
                " powershell",
                " pwsh",
            ],
            "starts_with": [],
            "wrong_sep": "\\",
            "right_sep": "/",
        },
        "zsh": {
            "forbidden_tokens": [
                " findstr",
                " dir ",
                " type ",
                " cls",
                " powershell",
                " pwsh",
            ],
            "starts_with": [],
            "wrong_sep": "\\",
            "right_sep": "/",
        },
        "fish": {
            "forbidden_tokens": [
                " findstr",
                " dir ",
                " type ",
                " cls",
                " powershell",
                " pwsh",
            ],
            "starts_with": [],
            "wrong_sep": "\\",
            "right_sep": "/",
        },
    }

    # Heuristic patterns that strongly indicate PowerShell
    POWERSHELL_HINTS = [
        r"^\s*(Get|Set|New|Remove|Add|Import|Export|Invoke|Test|Update|ConvertTo|ConvertFrom|Write)-\w+",
        r"\s-\w+",
        r"\$\w+",
    ]

    # Heuristic patterns that strongly indicate CMD/batch
    CMD_HINTS = [
        r"^\s*for\s+/F",
        r"^\s*set\s+",
        r"^\s*echo\s+",
        r"\s&&\s",  # also used in POSIX shells, heuristic only
        r"\s\|\|\s",  # heuristic
    ]

    def detect_environment(self) -> Dict[str, str]:
        shell_name = ""
        os_name = platform_utils.get_platform_info().get("os_name", "").lower()
        sh = platform_utils.detect_shell()
        if sh:
            shell_name = (sh[0] or "").lower()
        return {"os": os_name, "shell": shell_name}

    def _is_windows(self, os_name: str) -> bool:
        return os_name.startswith("win")

    def _has_wrong_path_separators(
        self, command: str, wrong_sep: str, right_sep: str
    ) -> bool:
        # If the command uses only the wrong separator and omits the right one,
        # treat this as likely incompatible path formatting.
        return (wrong_sep in command) and (right_sep not in command)

    def _has_forbidden_tokens(self, command_lc: str, tokens: List[str]) -> List[str]:
        found: List[str] = []
        for token in tokens:
            if token in command_lc:
                found.append(token.strip())
        return found

    def _matches_any(self, command: str, patterns: List[str]) -> bool:
        for pat in patterns:
            try:
                if re.search(pat, command, flags=re.IGNORECASE):
                    return True
            except re.error:
                # ignore bad regex patterns
                continue
        return False

    def validate_for_environment(
        self,
        command: str,
        shell_override: Optional[str] = None,
        os_override: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a command for the current or overridden OS/shell environment.

        Args:
            command: the command string
            shell_override: force validation as if running in this shell name
            os_override: force validation as if running on this OS name

        Returns:
            ValidationResult with strict rejection details.
        """
        result = ValidationResult(is_valid=True)
        env = self.detect_environment()
        os_name = (os_override or env["os"] or "").lower()
        shell_name = (shell_override or env["shell"] or "").lower()

        command_lc = (
            f" {command.strip().lower()} "  # padded for simple ' token ' checks
        )

        # 1) Unknown environment - be conservative
        if not os_name or not shell_name:
            # Still run basic checks if possible
            pass

        # 2) Per-shell forbidden tokens and path rules
        rules = self.FORBIDDEN_BY_SHELL.get(shell_name)
        if rules:
            # Forbidden tokens
            forbidden = self._has_forbidden_tokens(
                command_lc, rules.get("forbidden_tokens", [])
            )
            if forbidden:
                result.is_valid = False
                result.add(
                    "forbidden_token",
                    "Command contains tokens forbidden for the detected shell.",
                    {"shell": shell_name, "tokens": forbidden},
                )

            # Path separator check (heuristic: only complain if seems to contain paths)
            wrong_sep = rules.get("wrong_sep", "")
            right_sep = rules.get("right_sep", "")
            if (
                wrong_sep
                and right_sep
                and self._has_wrong_path_separators(command, wrong_sep, right_sep)
            ):
                # Skip if the command clearly lacks any path-like segment.
                looks_like_path = ("/" in command) or ("\\" in command)
                if looks_like_path:
                    result.is_valid = False
                    result.add(
                        "path_separator",
                        ("Command uses the wrong path separator for this shell."),
                        {
                            "shell": shell_name,
                            "required": right_sep,
                            "found_wrong": wrong_sep,
                        },
                    )

        # 3) OS/shell coherence heuristics
        if not self._is_windows(os_name) and shell_name in {
            "powershell",
            "pwsh",
            "cmd",
        }:
            # On Unix, reject Windows shell heuristics if the command looks
            # Windows-specific.
            if self._matches_any(command, self.POWERSHELL_HINTS) or self._matches_any(
                command, self.CMD_HINTS
            ):
                result.is_valid = False
                result.add(
                    "os_shell_mismatch",
                    ("Windows-specific shell syntax detected on a non-Windows OS."),
                    {"os": os_name, "shell": shell_name},
                )

        # 4) Lightweight syntax hints (PowerShell-specific verbs in non-PS shells)
        # Only apply when the command actually resembles PowerShell syntax,
        # not for generic Unix commands like "ls -la".
        if shell_name not in {"powershell", "pwsh"}:
            # Heuristic: If the command has a dash-prefixed option alongside a
            # typical POSIX command, avoid flagging as PowerShell. Prevents
            # false positives for e.g. "ls -la".
            posix_common = [
                r"\bls\b",
                r"\bgrep\b",
                r"\bcat\b",
                r"\bchmod\b",
                r"\bchown\b",
                r"\btar\b",
                r"\bfind\b",
            ]
            looks_posix = any(
                re.search(p, command, flags=re.IGNORECASE) for p in posix_common
            )
            if self._matches_any(command, self.POWERSHELL_HINTS) and not looks_posix:
                result.is_valid = False
                result.add(
                    "shell_syntax_mismatch",
                    (
                        "PowerShell-specific syntax detected but current shell "
                        "is not PowerShell."
                    ),
                    {"shell": shell_name},
                )

        # 5) If Windows CMD but command looks Unix-only (heuristic)
        if shell_name == "cmd":
            unix_only_hints = [r"\bsudo\b", r"\bchmod\b", r"\bchown\b", r"~/", r"\$\w+"]
            if self._matches_any(command, unix_only_hints):
                result.is_valid = False
                result.add(
                    "shell_syntax_mismatch",
                    "Unix-specific syntax detected but current shell is CMD.",
                    {"shell": shell_name},
                )

        return result
