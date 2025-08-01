"""
Settings management for CommandRex.

This module provides functions to manage application settings,
including loading, saving, and accessing configuration values.
"""

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Import from our own modules
from commandrex.executor import platform_utils


class Settings:
    """
    Settings manager for CommandRex.

    This class handles loading, saving, and accessing application settings.
    """

    # Default settings
    DEFAULT_SETTINGS = {
        "api": {
            "model": "gpt-4.1-mini-2025-04-14",
            "temperature": 0.2,
            "max_tokens": 1000,
            "timeout": 30,
        },
        "ui": {
            "theme": "dark",
            "animation_speed": 1.0,
            "max_history": 100,
            "show_command_components": True,
            "syntax_highlighting": True,
            "show_welcome_screen": True,
        },
        "commands": {
            "confirm_dangerous": True,
            "history_file": "",
            "timeout": 60,
            "max_output_lines": 1000,
        },
        "security": {
            "allow_sudo": False,
            "allow_network": True,
            "allow_file_operations": True,
            "dangerous_commands_require_confirmation": True,
        },
        "advanced": {
            "debug_mode": False,
            "log_level": "INFO",
            "log_file": "",
        },
    }

    def __init__(self):
        """Initialize the settings manager."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "settings.json"

        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)

        # Load settings from file if it exists
        if self.config_file.exists():
            self.load()

    def _get_config_dir(self) -> Path:
        """
        Get the configuration directory for the application.

        Returns:
            Path: Path to the configuration directory.
        """
        if platform_utils.is_windows():
            # Windows: %APPDATA%\CommandRex
            return Path(os.environ.get("APPDATA", "")) / "CommandRex"

        elif platform_utils.is_macos():
            # macOS: ~/Library/Application Support/CommandRex
            return Path.home() / "Library" / "Application Support" / "CommandRex"

        else:
            # Linux/Unix: ~/.config/commandrex
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config_home:
                return Path(xdg_config_home) / "commandrex"
            else:
                return Path.home() / ".config" / "commandrex"

    def load(self) -> bool:
        """
        Load settings from the configuration file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded_settings = json.load(f)

            # Update settings with loaded values
            self._update_nested_dict(self.settings, loaded_settings)
            return True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}")
            return False

    def save(self) -> bool:
        """
        Save settings to the configuration file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            return True

        except IOError as e:
            print(f"Error saving settings: {e}")
            return False

    def _update_nested_dict(self, target: Dict, source: Dict) -> None:
        """
        Update a nested dictionary with values from another dictionary.

        Args:
            target (Dict): Target dictionary to update.
            source (Dict): Source dictionary with new values.
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively update nested dictionaries
                self._update_nested_dict(target[key], value)
            else:
                # Update or add the value
                target[key] = value

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            section (str): Settings section.
            key (str): Setting key.
            default (Any): Default value if not found.

        Returns:
            Any: Setting value or default.
        """
        try:
            return self.settings[section][key]
        except KeyError:
            return default

    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a setting value.

        Args:
            section (str): Settings section.
            key (str): Setting key.
            value (Any): Setting value.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if section not in self.settings:
                self.settings[section] = {}

            self.settings[section][key] = value
            return True

        except Exception as e:
            print(f"Error setting {section}.{key}: {e}")
            return False

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings.

        Returns:
            Dict[str, Dict[str, Any]]: All settings.
        """
        return copy.deepcopy(self.settings)

    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)

    def reset_section(self, section: str) -> bool:
        """
        Reset a section to default values.

        Args:
            section (str): Settings section.

        Returns:
            bool: True if successful, False otherwise.
        """
        if section in self.DEFAULT_SETTINGS:
            self.settings[section] = copy.deepcopy(self.DEFAULT_SETTINGS[section])
            return True
        return False

    def get_history_file_path(self) -> Path:
        """
        Get the path to the command history file.

        Returns:
            Path: Path to the history file.
        """
        history_file = self.get("commands", "history_file", "")

        if history_file:
            return Path(history_file)
        else:
            # Default history file in config directory
            return self.config_dir / "command_history.json"

    def get_log_file_path(self) -> Optional[Path]:
        """
        Get the path to the log file.

        Returns:
            Optional[Path]: Path to the log file, or None if not set.
        """
        log_file = self.get("advanced", "log_file", "")

        if log_file:
            return Path(log_file)
        elif self.get("advanced", "debug_mode", False):
            # Default log file in config directory if debug mode is enabled
            return self.config_dir / "commandrex.log"
        else:
            return None

    def is_dangerous_command_allowed(self, command_type: str) -> bool:
        """
        Check if a dangerous command type is allowed.

        Args:
            command_type (str): Type of command (sudo, network, file_operations).

        Returns:
            bool: True if allowed, False otherwise.
        """
        security_settings = self.settings.get("security", {})

        if command_type == "sudo":
            return security_settings.get("allow_sudo", False)

        elif command_type == "network":
            return security_settings.get("allow_network", True)

        elif command_type == "file_operations":
            return security_settings.get("allow_file_operations", True)

        # Default to requiring confirmation for unknown command types
        return False

    def requires_confirmation(self, is_dangerous: bool) -> bool:
        """
        Check if a command requires confirmation based on its danger level.

        Args:
            is_dangerous (bool): Whether the command is dangerous.

        Returns:
            bool: True if confirmation is required, False otherwise.
        """
        if is_dangerous:
            return self.get("security", "dangerous_commands_require_confirmation", True)

        return False


# Global settings instance
settings = Settings()
