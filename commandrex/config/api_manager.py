"""
API key management for CommandRex.

This module handles secure storage and retrieval of API keys
using the system keyring.
"""

import logging
import os
from typing import Optional

import keyring

# Constants
SERVICE_NAME = "commandrex"
API_KEY_NAME = "openai_api_key"
ENV_VAR_NAME = "OPENAI_API_KEY"

logger = logging.getLogger(__name__)


def get_api_key() -> Optional[str]:
    """
    Retrieve the OpenAI API key from keyring or environment variable.

    Returns:
        str or None: The API key if found, None otherwise.
    """
    # First try to get from keyring
    api_key = keyring.get_password(SERVICE_NAME, API_KEY_NAME)

    # If not in keyring, try environment variable
    if not api_key:
        api_key = os.environ.get(ENV_VAR_NAME)
        if api_key:
            logger.info(f"Using API key from environment variable {ENV_VAR_NAME}")

    return api_key


def save_api_key(api_key: str) -> bool:
    """
    Save the OpenAI API key to the system keyring.

    Args:
        api_key (str): The API key to save.

    Returns:
        bool: True if successful, False otherwise.
    """
    if not api_key or not api_key.strip():
        logger.error("Cannot save empty API key")
        return False

    try:
        keyring.set_password(SERVICE_NAME, API_KEY_NAME, api_key)
        logger.info("API key saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save API key: {str(e)}")
        return False


def delete_api_key() -> bool:
    """
    Delete the stored API key from the system keyring.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        keyring.delete_password(SERVICE_NAME, API_KEY_NAME)
        logger.info("API key deleted successfully")
        return True
    except keyring.errors.PasswordDeleteError:
        # Key might not exist, which is fine
        logger.info("No API key found to delete")
        return True
    except Exception as e:
        logger.error(f"Failed to delete API key: {str(e)}")
        return False


def is_api_key_valid(api_key: str) -> bool:
    """
    Validate the format of an OpenAI API key.

    Args:
        api_key (str): The API key to validate.

    Returns:
        bool: True if the key format is valid, False otherwise.
    """
    if not api_key or not isinstance(api_key, str):
        return False

    # Check for whitespace (leading/trailing spaces are invalid)
    if api_key != api_key.strip():
        return False

    # OpenAI API keys must start with "sk-" (case sensitive) and be at least 43 characters long total
    return api_key.startswith("sk-") and len(api_key) >= 43
