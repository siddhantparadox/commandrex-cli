"""
OpenAI API client for CommandRex.

This module provides an async client for interacting with the OpenAI API,
handling authentication, rate limiting, and error handling.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

import httpx
from openai import APIError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel

# Import from our own modules
from commandrex.config import api_manager
from commandrex.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)


class CommandTranslationResult(BaseModel):
    """Model for command translation results."""

    command: str
    explanation: str
    safety_assessment: Dict[str, Any]
    components: List[Dict[str, str]]
    is_dangerous: bool
    alternatives: Optional[List[str]] = None


class OpenAIClient:
    """
    Async client for interacting with the OpenAI API.

    This class handles authentication, rate limiting, and error handling
    for OpenAI API requests.
    """

    def __init__(
        self, api_key: Optional[str] = None, model: str = "gpt-5-mini-2025-08-07"
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key (Optional[str]): OpenAI API key. If None, will attempt to
                retrieve from keyring.
            model (str): The model to use for completions. Defaults to
                "gpt-5-mini-2025-08-07".
        """
        self.api_key = api_key or api_manager.get_api_key()
        if not self.api_key:
            logger.error("No API key provided or found in keyring")
            raise ValueError("OpenAI API key is required")

        if not api_manager.is_api_key_valid(self.api_key):
            logger.error("Invalid API key format")
            raise ValueError("Invalid OpenAI API key format")

        self.model = model

        # Rate limiting parameters
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds between requests

        logger.info(f"OpenAI client initialized with model {model}")

    async def _handle_rate_limit(self) -> None:
        """
        Handle rate limiting by ensuring minimum time between requests.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            delay = self.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: waiting {delay:.2f} seconds")
            await asyncio.sleep(delay)

        self.last_request_time = time.time()

    async def translate_to_command(
        self,
        natural_language: str,
        system_info: Dict[str, Any],
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> CommandTranslationResult:  # pragma: no cover - external API
        """
        Translate natural language to a shell command.

        Args:
            natural_language (str): The natural language request.
            system_info (Dict[str, Any]): System information to provide context.
            stream_callback (Optional[Callable]): Callback for streaming responses.

        Returns:
            CommandTranslationResult: The translated command with metadata.

        Raises:
            APIError: If there's an error communicating with the OpenAI API.
            ValueError: If the response cannot be parsed.
        """
        await self._handle_rate_limit()

        try:
            # Build strict system message with environment constraints to ensure
            # only commands valid for the detected OS/shell are generated.
            from commandrex.executor import platform_utils

            # Extract OS/shell info, with safe defaults
            platform_info = system_info or {}
            os_name = (
                platform_info.get("os_name") or ""
            ).lower() or platform_utils.get_platform_info().get("os_name", "Unknown")
            shell_info = platform_utils.detect_shell()
            detected_shell = (shell_info[0] if shell_info else "") or platform_info.get(
                "shell_name", ""
            )

            # Derive strict rules similar to PromptBuilder.STRICT_ENVIRONMENT_RULES
            # to harden the system prompt at the client layer as well.
            strict_rules = {
                "cmd": {
                    "forbidden": [
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
                    "path_sep": "\\\\",
                    "wrong_sep": "/",
                },
                "powershell": {
                    "forbidden": [
                        "grep",
                        "cat",
                        "sed",
                        "awk",
                        "chmod",
                        "chown",
                        "sudo",
                    ],
                    "path_sep": "\\\\",
                    "wrong_sep": "/",
                },
                "pwsh": {
                    "forbidden": [
                        "grep",
                        "cat",
                        "sed",
                        "awk",
                        "chmod",
                        "chown",
                        "sudo",
                    ],
                    "path_sep": "\\\\",
                    "wrong_sep": "/",
                },
                "bash": {
                    "forbidden": [
                        "dir",
                        "type ",
                        "findstr",
                        "cls",
                        "powershell",
                        "pwsh",
                    ],
                    "path_sep": "/",
                    "wrong_sep": "\\\\",
                },
                "zsh": {
                    "forbidden": [
                        "dir",
                        "type ",
                        "findstr",
                        "cls",
                        "powershell",
                        "pwsh",
                    ],
                    "path_sep": "/",
                    "wrong_sep": "\\\\",
                },
                "fish": {
                    "forbidden": [
                        "dir",
                        "type ",
                        "findstr",
                        "cls",
                        "powershell",
                        "pwsh",
                    ],
                    "path_sep": "/",
                    "wrong_sep": "\\\\",
                },
            }

            shell_key = (detected_shell or "").lower()
            rules = strict_rules.get(shell_key, None)

            # Core schema lines (kept compact to satisfy E501 elsewhere)
            schema_lines = [
                "You are CommandRex, an expert in translating natural language into "
                "terminal commands.",
                "Return a single command appropriate for the user's OS and shell.",
                "Respond as strict JSON with this structure:",
                "{",
                '  "command": "string",',
                '  "explanation": "string",',
                '  "safety_assessment": { "is_safe": true|false, "concerns": [], '
                '"risk_level": "none|low|medium|high" },',
                '  "components": [ { "part": "token", "description": '
                '"what it does" } ],',
                '  "is_dangerous": true|false,',
                '  "alternatives": ["alt1", "alt2"]',
                "}",
            ]

            # Strict environment constraints
            strict_lines = []
            if rules:
                forbidden_list = ", ".join(rules["forbidden"])
                strict_lines.append("CRITICAL ENVIRONMENT CONSTRAINTS:")
                strict_lines.append(f"- Detected OS: {os_name}")
                strict_lines.append(f"- Detected Shell: {shell_key}")
                strict_lines.append(f"- FORBIDDEN commands: {forbidden_list}")
                strict_lines.append(
                    f"- REQUIRED path separator: '{rules['path_sep']}' "
                    f"(never use '{rules['wrong_sep']}')"
                )
                strict_lines.append(
                    "- NEVER mix syntax from other shells. Do not use Unix commands in "
                    "Windows shells or Windows commands in Unix shells."
                )
                strict_lines.append(
                    "- If a command is not available in this environment, choose a "
                    "functionally equivalent command that IS available."
                )

            messages = [
                {
                    "role": "system",
                    "content": "\n".join(
                        schema_lines + ([""] + strict_lines if strict_lines else [])
                    ),
                },
                {"role": "system", "content": f"System information: {system_info}"},
                {"role": "user", "content": natural_language},
            ]

            async with AsyncOpenAI(api_key=self.api_key) as client:
                if stream_callback:
                    # Streaming response for real-time feedback
                    stream = await client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        stream=True,
                        response_format={"type": "json_object"},
                    )

                    collected_chunks = []
                    async for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            collected_chunks.append(content)
                            if stream_callback:
                                stream_callback(content)

                    full_response = "".join(collected_chunks)
                else:
                    # Non-streaming response
                    response = await client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                    )
                    full_response = response.choices[0].message.content

            # Parse the response
            try:
                import json

                response_data = json.loads(full_response)

                # Extract the command and metadata
                command = response_data.get("command", "")
                explanation = response_data.get("explanation", "")
                safety = response_data.get("safety_assessment", {})
                components = response_data.get("components", [])
                is_dangerous = response_data.get("is_dangerous", False)
                alternatives = response_data.get("alternatives", [])

                # Post-generation validation (Phase 1 strict):
                # Enforce environment-aware validation and reject incompatible commands.
                # Respect settings toggles for strictness and suggestions.
                strict_mode = settings.get("validation", "strict_mode", True)
                suggest_alts = settings.get("validation", "suggest_alternatives", True)
                try:
                    from commandrex.validator.command_validator import (  # noqa: E402
                        CommandValidator,
                    )

                    validator = CommandValidator()
                    # Use detected shell/os where possible
                    os_name_val = os_name
                    shell_name_val = shell_key
                    validation = validator.validate_for_environment(
                        command, shell_override=shell_name_val, os_override=os_name_val
                    )
                    if not validation.is_valid:
                        issues_text = "; ".join(validation.reasons)
                        logger.error(
                            "Rejected command due to environment validation: %s",
                            issues_text,
                        )
                        if strict_mode:
                            raise ValueError(
                                "Generated command is incompatible with the current "
                                f"environment: {issues_text}"
                            )
                        # Non-strict mode: keep the command but annotate explanation
                        if suggest_alts:
                            explanation = (
                                f"{explanation}\nEnvironment validation issues: "
                                + issues_text
                            )
                except ImportError:
                    # If validator module is unavailable, fall back to previous
                    # lite checks while keeping lines within E501 limits.
                    issues: List[str] = []
                    shell_rules = strict_rules.get(shell_key) if rules else None
                    if shell_rules:
                        for fbd in shell_rules["forbidden"]:
                            starts_forbidden = command.lower().startswith(fbd)
                            has_token = f"{fbd} " in command
                            if has_token or starts_forbidden:
                                issues.append(
                                    f"Forbidden command for {shell_key}: {fbd}"
                                )
                        wrong_sep = shell_rules["wrong_sep"]
                        right_sep = shell_rules["path_sep"]
                        wrong_only = wrong_sep in command and right_sep not in command
                        if wrong_only:
                            issues.append(
                                "Wrong path separator "
                                f"'{wrong_sep}' for shell {shell_key}"
                            )
                    if issues:
                        logger.warning(
                            "LLM command did not pass environment validation "
                            "(fallback): %s",
                            issues,
                        )
                    if issues and suggest_alts:
                        explanation = (
                            f"{explanation}\nEnvironment validation issues detected: "
                            + "; ".join(issues)
                        )

                return CommandTranslationResult(
                    command=command,
                    explanation=explanation,
                    safety_assessment=safety,
                    components=components,
                    is_dangerous=is_dangerous,
                    alternatives=alternatives,
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse API response: {e}")
                raise ValueError(f"Failed to parse API response: {e}") from e

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise ValueError(
                f"OpenAI API rate limit exceeded. Please try again later: {e}"
            ) from e

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"Error communicating with OpenAI API: {e}") from e

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during API request: {e}")
            raise ValueError(f"Network error during API request: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ValueError(f"Unexpected error during command translation: {e}") from e

    async def get_command_options(
        self,
        natural_language: str,
        system_info: Dict[str, Any],
        num_options: int = 4,
    ) -> List[CommandTranslationResult]:  # pragma: no cover - external API
        """
        Ask the model for multiple alternative command options with explanations,
        components, expected outcome, and a coarse safety flag.
        """
        await self._handle_rate_limit()
        try:
            # Build concise, wrapped system message to satisfy line-length checks
            schema_lines = [
                "You are CommandRex, an expert in translating natural language "
                "into terminal commands.",
                f"Return BETWEEN 2 and {num_options} options best suited to the "
                "user's OS/shell.",
                "Each option must include ONLY: command, description, and components.",
                "IMPORTANT: Respond as strict JSON with this structure:",
                "{",
                '  "options": [',
                "    {",
                '      "command": "string",',
                '      "description": "string",',
                '      "components": [',
                '        { "part": "token", "description": "what it does",',
                '          "type": "command|subcommand|flag|argument|operator|pipe|'
                'redirection|other" }',
                "      ]",
                "    }",
                "  ]",
                "}",
            ]
            messages = [
                {
                    "role": "system",
                    "content": "\n".join(schema_lines),
                },
                {"role": "system", "content": f"System information: {system_info}"},
                {"role": "user", "content": natural_language},
            ]

            async with AsyncOpenAI(api_key=self.api_key) as client:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            import json

            payload = json.loads(response.choices[0].message.content or "{}")
            raw_options = payload.get("options", [])
            results: List[CommandTranslationResult] = []
            for opt in raw_options:
                cmd = opt.get("command", "")
                desc = opt.get("description", "")
                components = opt.get("components", []) or []
                # Map to CommandTranslationResult so callers can reuse render paths
                result = CommandTranslationResult(
                    command=cmd,
                    explanation=desc,
                    safety_assessment={"risk_level": "unknown", "concerns": []},
                    components=components,
                    is_dangerous=False,
                    alternatives=None,
                )
                results.append(result)

            # Fallback: if model returns nothing, degrade to single translate
            if not results:
                single = await self.translate_to_command(natural_language, system_info)
                results = [single]
            return results
        except Exception as e:
            logger.error(f"Error getting command options: {e}")
            raise ValueError(f"Error getting command options: {e}") from e

    async def explain_command(
        self, command: str
    ) -> Dict[str, Any]:  # pragma: no cover - external API
        """
        Generate an explanation for a given command.

        Args:
            command (str): The command to explain.

        Returns:
            Dict[str, Any]: Explanation and component breakdown.

        Raises:
            APIError: If there's an error communicating with the OpenAI API.
        """
        await self._handle_rate_limit()

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are CommandRex, an expert in explaining terminal "
                        "commands. "
                        "Your task is to explain the given command in a clear, "
                        "educational way. "
                        "Break down each component and explain what it does.\n\n"
                        "IMPORTANT: You must respond in JSON format with the following "
                        "structure:\n"
                        "{\n"
                        '  "explanation": "overall explanation of the command",\n'
                        '  "components": [\n'
                        '    {"part": "command_part", "description": "what this part '
                        'does"}\n'
                        "  ],\n"
                        '  "examples": ["example usage 1", "example usage 2"],\n'
                        '  "related_commands": ["related1", "related2"]\n'
                        "}\n"
                    ),
                },
                {"role": "user", "content": f"Explain this command: {command}"},
            ]

            async with AsyncOpenAI(api_key=self.api_key) as client:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )

            # Parse the response
            try:
                import json

                response_data = json.loads(response.choices[0].message.content)
                return response_data
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse API response: {e}")
                raise ValueError(f"Failed to parse API response: {e}") from e

        except Exception as e:
            logger.error(f"Error explaining command: {e}")
            raise ValueError(f"Error explaining command: {e}") from e

    async def assess_command_safety(
        self, command: str
    ) -> Dict[str, Any]:  # pragma: no cover - external API
        """
        Assess the safety of a given command.

        Args:
            command (str): The command to assess.

        Returns:
            Dict[str, Any]: Safety assessment.

        Raises:
            APIError: If there's an error communicating with the OpenAI API.
        """
        await self._handle_rate_limit()

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are CommandRex, an expert in terminal command safety. "
                        "Your task is to assess the safety of the given command. "
                        "Identify any potentially dangerous operations, such as file "
                        "deletion, "
                        "system modifications, or network operations.\n\n"
                        "IMPORTANT: You must respond in JSON format with the following "
                        "structure:\n"
                        "{\n"
                        '  "is_safe": true/false,\n'
                        '  "risk_level": "none/low/medium/high",\n'
                        '  "concerns": ["concern1", "concern2"],\n'
                        '  "recommendations": ["recommendation1", "recommendation2"],\n'
                        '  "safer_alternatives": ["alternative1", "alternative2"]\n'
                        "}\n"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Assess the safety of this command: {command}",
                },
            ]

            async with AsyncOpenAI(api_key=self.api_key) as client:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )

            # Parse the response
            try:
                import json

                response_data = json.loads(response.choices[0].message.content)
                return response_data
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse API response: {e}")
                raise ValueError(f"Failed to parse API response: {e}") from e

        except Exception as e:
            logger.error(f"Error assessing command safety: {e}")
            raise ValueError(f"Error assessing command safety: {e}") from e
