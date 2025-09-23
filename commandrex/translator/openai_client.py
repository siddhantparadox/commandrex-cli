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

    def _reasoning_kwargs(self) -> Optional[Dict[str, str]]:
        """Return reasoning kwargs when the current model supports it."""

        reasoning_prefixes = ("gpt-5", "o1", "o3")
        if any(self.model.startswith(prefix) for prefix in reasoning_prefixes):
            return {"effort": "medium"}
        return None

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

    def _ensure_responses_resource(self, client: AsyncOpenAI):
        """Ensure the AsyncOpenAI client exposes the Responses API resource."""

        responses_resource = getattr(client, "responses", None)
        if responses_resource is not None:
            return responses_resource

        try:
            from openai.resources.responses import AsyncResponses  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on SDK
            logger.error(
                "AsyncOpenAI.responses is unavailable; installed openai package "
                "lacks Responses API support: %s",
                exc,
            )
            raise RuntimeError(
                "The installed openai client is missing Responses API support. "
                "Please upgrade to openai>=1.65.2."
            ) from exc

        responses_resource = AsyncResponses(client)
        client.responses = responses_resource
        return responses_resource

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

            # Build Responses API input structure
            input_items = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "\n".join(
                                schema_lines
                                + ([""] + strict_lines if strict_lines else [])
                            ),
                        }
                    ],
                },
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"System information: {system_info}",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": natural_language},
                    ],
                },
            ]

            # JSON schema for strict JSON output
            json_schema = {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "explanation": {"type": "string"},
                    "safety_assessment": {
                        "type": "object",
                        "properties": {
                            "is_safe": {"type": ["boolean", "null"]},
                            "concerns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "risk_level": {
                                "type": "string",
                                "enum": [
                                    "none",
                                    "low",
                                    "medium",
                                    "high",
                                    "unknown",
                                ],
                                "default": "unknown",
                            },
                        },
                        "additionalProperties": True,
                        "default": {},
                    },
                    "components": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "part": {"type": "string"},
                                "description": {"type": "string"},
                                "type": {"type": "string"},
                            },
                            "additionalProperties": True,
                        },
                        "default": [],
                    },
                    "is_dangerous": {"type": "boolean", "default": False},
                    "alternatives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            }

            text_format = {
                "format": {
                    "type": "json_schema",
                    "name": "CommandTranslation",
                    "schema": json_schema,
                    "strict": True,
                }
            }

            async with AsyncOpenAI(api_key=self.api_key) as client:
                responses_resource = self._ensure_responses_resource(client)
                if stream_callback:
                    # Streaming via Responses API
                    stream_method = getattr(responses_resource, "stream", None)
                    if stream_method is None:
                        raise RuntimeError(
                            "The installed openai client does not support streaming "
                            "Responses API calls."
                        )
                    stream_kwargs = {
                        "model": self.model,
                        "input": input_items,
                        "text": text_format,
                        "store": False,
                    }
                    reasoning_args = self._reasoning_kwargs()
                    if reasoning_args:
                        stream_kwargs["reasoning"] = reasoning_args

                    stream = await stream_method(**stream_kwargs)

                    collected_chunks: List[str] = []
                    async for event in stream:
                        # Only capture text deltas for output
                        et = getattr(event, "type", None)
                        if et == "response.output_text.delta":
                            piece = getattr(event, "delta", None)
                            if piece:
                                collected_chunks.append(piece)
                                if stream_callback:
                                    stream_callback(piece)
                    # Fetch the final response to ensure completion if available
                    final_output_text = ""
                    try:
                        get_final = getattr(stream, "get_final_response", None)
                        if get_final is not None:
                            final = await get_final()
                            final_output_text = getattr(final, "output_text", "")
                    except Exception:
                        final_output_text = ""
                    full_response = "".join(collected_chunks) or final_output_text
                else:
                    # Non-streaming response via Responses API
                    create_method = getattr(responses_resource, "create", None)
                    if create_method is None:
                        raise RuntimeError(
                            "The installed openai client does not support Responses API "
                            "create calls."
                        )
                    create_kwargs = {
                        "model": self.model,
                        "input": input_items,
                        "text": text_format,
                        "store": False,
                    }
                    reasoning_args = self._reasoning_kwargs()
                    if reasoning_args:
                        create_kwargs["reasoning"] = reasoning_args

                    response = await create_method(**create_kwargs)
                    # Prefer convenience property when available
                    full_response = getattr(response, "output_text", None) or ""
                    if not full_response:
                        # Fallback: join output_text parts if present
                        try:
                            outputs = getattr(response, "output", [])
                            parts = []
                            for item in outputs:
                                if getattr(item, "type", None) == "output_text":
                                    parts.append(getattr(item, "text", ""))
                            full_response = "".join(parts)
                        except Exception:
                            full_response = ""

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
            input_items = [
                {
                    "role": "system",
                    "content": [
                        {"type": "input_text", "text": "\n".join(schema_lines)}
                    ],
                },
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"System information: {system_info}",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": natural_language},
                    ],
                },
            ]

            # Simple schema for options array
            options_schema = {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                                "description": {"type": "string"},
                                "components": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "part": {"type": "string"},
                                            "description": {"type": "string"},
                                            "type": {
                                                "type": "string",
                                                "enum": [
                                                    "command",
                                                    "subcommand",
                                                    "flag",
                                                    "argument",
                                                    "operator",
                                                    "pipe",
                                                    "redirection",
                                                    "other",
                                                ],
                                            },
                                        },
                                        "required": ["part", "description", "type"],
                                        "additionalProperties": False,
                                    },
                                    "default": [],
                                },
                            },
                            "required": ["command", "description", "components"],
                            "additionalProperties": False,
                        },
                        "default": [],
                    }
                },
                "required": ["options"],
                "additionalProperties": False,
            }

            text_format = {
                "format": {
                    "type": "json_schema",
                    "name": "CommandOptions",
                    "schema": options_schema,
                    "strict": True,
                }
            }

            async with AsyncOpenAI(api_key=self.api_key) as client:
                responses_resource = self._ensure_responses_resource(client)
                create_method = getattr(responses_resource, "create", None)
                if create_method is None:
                    raise RuntimeError(
                        "The installed openai client does not support Responses API "
                        "create calls."
                    )
                request_kwargs = {
                    "model": self.model,
                    "input": input_items,
                    "text": text_format,
                    "store": False,
                }
                reasoning_args = self._reasoning_kwargs()
                if reasoning_args:
                    request_kwargs["reasoning"] = reasoning_args

                response = await create_method(**request_kwargs)
            import json

            payload = json.loads(getattr(response, "output_text", "{}") or "{}")
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
            input_items = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are CommandRex, an expert in explaining terminal "
                                "commands. "
                                "Your task is to explain the given command in a clear, "
                                "educational way. "
                                "Break down each component and explain what it does.\n\n"
                                "IMPORTANT: Respond in JSON with keys: explanation, components, "
                                "examples, related_commands."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Explain this command: {command}",
                        }
                    ],
                },
            ]

            schema = {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string"},
                    "components": {"type": "array"},
                    "examples": {"type": "array"},
                    "related_commands": {"type": "array"},
                },
                "required": ["explanation", "components"],
                "additionalProperties": False,
            }

            text_format = {
                "format": {
                    "type": "json_schema",
                    "name": "ExplainCommand",
                    "schema": schema,
                    "strict": True,
                }
            }

            async with AsyncOpenAI(api_key=self.api_key) as client:
                responses_resource = self._ensure_responses_resource(client)
                create_method = getattr(responses_resource, "create", None)
                if create_method is None:
                    raise RuntimeError(
                        "The installed openai client does not support Responses API "
                        "create calls."
                    )
                options_kwargs = {
                    "model": self.model,
                    "input": input_items,
                    "text": text_format,
                    "store": False,
                }
                reasoning_args = self._reasoning_kwargs()
                if reasoning_args:
                    options_kwargs["reasoning"] = reasoning_args

                response = await create_method(**options_kwargs)

            # Parse the response
            try:
                import json

                response_data = json.loads(getattr(response, "output_text", "{}"))
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
            input_items = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are CommandRex, an expert in terminal command safety. "
                                "Assess the safety of the given command. Identify dangerous "
                                "operations and propose safer alternatives."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Assess the safety of this command: {command}",
                        }
                    ],
                },
            ]

            schema = {
                "type": "object",
                "properties": {
                    "is_safe": {"type": "boolean"},
                    "risk_level": {
                        "type": "string",
                        "enum": ["none", "low", "medium", "high"],
                    },
                    "concerns": {"type": "array"},
                    "recommendations": {"type": "array"},
                    "safer_alternatives": {"type": "array"},
                },
                "required": ["is_safe", "risk_level"],
                "additionalProperties": False,
            }

            text_format = {
                "format": {
                    "type": "json_schema",
                    "name": "SafetyAssessment",
                    "schema": schema,
                    "strict": True,
                }
            }

            async with AsyncOpenAI(api_key=self.api_key) as client:
                responses_resource = self._ensure_responses_resource(client)
                create_method = getattr(responses_resource, "create", None)
                if create_method is None:
                    raise RuntimeError(
                        "The installed openai client does not support Responses API "
                        "create calls."
                    )
                safety_kwargs = {
                    "model": self.model,
                    "input": input_items,
                    "text": text_format,
                    "store": False,
                }
                reasoning_args = self._reasoning_kwargs()
                if reasoning_args:
                    safety_kwargs["reasoning"] = reasoning_args

                response = await create_method(**safety_kwargs)

            # Parse the response
            try:
                import json

                response_data = json.loads(getattr(response, "output_text", "{}"))
                return response_data
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse API response: {e}")
                raise ValueError(f"Failed to parse API response: {e}") from e

        except Exception as e:
            logger.error(f"Error assessing command safety: {e}")
            raise ValueError(f"Error assessing command safety: {e}") from e
