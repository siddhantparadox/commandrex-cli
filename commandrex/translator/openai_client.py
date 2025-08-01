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
        self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini-2025-04-14"
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key (Optional[str]): OpenAI API key. If None, will attempt to
                retrieve from keyring.
            model (str): The model to use for completions. Defaults to
                "gpt-4.1-mini-2025-04-14".
        """
        self.api_key = api_key or api_manager.get_api_key()
        if not self.api_key:
            logger.error("No API key provided or found in keyring")
            raise ValueError("OpenAI API key is required")

        if not api_manager.is_api_key_valid(self.api_key):
            logger.error("Invalid API key format")
            raise ValueError("Invalid OpenAI API key format")

        self.model = model
        self.client = AsyncOpenAI(api_key=self.api_key)

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
    ) -> CommandTranslationResult:
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
            # This is a simplified version - in a real implementation,
            # we would use a more sophisticated prompt with proper formatting
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are CommandRex, an expert in translating natural language "
                        "into "
                        "terminal commands. Your task is to convert user requests into "
                        "the most "
                        "appropriate command for their system. Provide the command, an "
                        "explanation, "
                        "and a safety assessment.\n\n"
                        "IMPORTANT: You must respond in JSON format with the following "
                        "structure:\n"
                        "{\n"
                        '  "command": "the command to execute",\n'
                        '  "explanation": "explanation of what the command does",\n'
                        '  "safety_assessment": {\n'
                        '    "is_safe": true/false,\n'
                        '    "concerns": ["list", "of", "concerns"],\n'
                        '    "risk_level": "low/medium/high"\n'
                        "  },\n"
                        '  "components": [\n'
                        '    {"part": "command_part", "description": "what this part '
                        'does"}\n'
                        "  ],\n"
                        '  "is_dangerous": true/false,\n'
                        '  "alternatives": ["alternative1", "alternative2"]\n'
                        "}\n"
                    ),
                },
                {"role": "system", "content": f"System information: {system_info}"},
                {"role": "user", "content": natural_language},
            ]

            if stream_callback:
                # Streaming response for real-time feedback
                stream = await self.client.chat.completions.create(
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
                response = await self.client.chat.completions.create(
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
    ) -> List[CommandTranslationResult]:
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

            response = await self.client.chat.completions.create(
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

    async def explain_command(self, command: str) -> Dict[str, Any]:
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

            response = await self.client.chat.completions.create(
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

    async def assess_command_safety(self, command: str) -> Dict[str, Any]:
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

            response = await self.client.chat.completions.create(
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
