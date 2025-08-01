"""
Unit tests for the settings module.

This module tests the settings management functionality including:
- Settings initialization and defaults
- Loading and saving settings
- Configuration directory detection
- Settings access and modification
- Platform-specific paths
- File path utilities
- Security settings validation
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commandrex.config.settings import Settings


@pytest.fixture
def isolated_settings():
    """Create an isolated settings instance for testing."""
    import copy

    with patch("commandrex.config.settings.os.makedirs"):
        settings = Settings()
        # Reset to clean defaults with deep copy
        settings.settings = copy.deepcopy(settings.DEFAULT_SETTINGS)
        return settings


class TestSettingsInitialization:
    """Test settings initialization and defaults."""

    def test_settings_initialization(self, isolated_settings):
        """Test settings initialization with defaults."""
        settings = isolated_settings

        # Check that default settings are loaded
        assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"
        assert settings.settings["api"]["temperature"] == 0.2
        assert settings.settings["ui"]["theme"] == "dark"
        assert settings.settings["commands"]["confirm_dangerous"] is True
        assert settings.settings["security"]["allow_sudo"] is False
        assert settings.settings["advanced"]["debug_mode"] is False

    def test_default_settings_structure(self, isolated_settings):
        """Test that default settings have the correct structure."""
        settings = isolated_settings

        # Check all required sections exist
        assert "api" in settings.settings
        assert "ui" in settings.settings
        assert "commands" in settings.settings
        assert "security" in settings.settings
        assert "advanced" in settings.settings

        # Check API section
        api_settings = settings.settings["api"]
        assert "model" in api_settings
        assert "temperature" in api_settings
        assert "max_tokens" in api_settings
        assert "timeout" in api_settings

        # Check UI section
        ui_settings = settings.settings["ui"]
        assert "theme" in ui_settings
        assert "animation_speed" in ui_settings
        assert "max_history" in ui_settings
        assert "show_command_components" in ui_settings
        assert "syntax_highlighting" in ui_settings

        # Check commands section
        commands_settings = settings.settings["commands"]
        assert "confirm_dangerous" in commands_settings
        assert "history_file" in commands_settings
        assert "timeout" in commands_settings
        assert "max_output_lines" in commands_settings

        # Check security section
        security_settings = settings.settings["security"]
        assert "allow_sudo" in security_settings
        assert "allow_network" in security_settings
        assert "allow_file_operations" in security_settings
        assert "dangerous_commands_require_confirmation" in security_settings

        # Check advanced section
        advanced_settings = settings.settings["advanced"]
        assert "debug_mode" in advanced_settings
        assert "log_level" in advanced_settings
        assert "log_file" in advanced_settings


class TestConfigurationDirectory:
    """Test configuration directory detection."""

    @patch("commandrex.config.settings.os.makedirs")
    @patch("commandrex.config.settings.platform_utils.is_windows")
    @patch("commandrex.config.settings.os.environ.get")
    def test_get_config_dir_windows(self, mock_env_get, mock_is_windows, mock_makedirs):
        """Test Windows configuration directory."""
        mock_is_windows.return_value = True
        mock_env_get.return_value = "C:\\Users\\Test\\AppData\\Roaming"

        settings = Settings()
        config_dir = settings._get_config_dir()

        assert config_dir == Path("C:\\Users\\Test\\AppData\\Roaming") / "CommandRex"
        mock_env_get.assert_called_with("APPDATA", "")

    @patch("commandrex.config.settings.os.makedirs")
    @patch("commandrex.config.settings.platform_utils.is_windows")
    @patch("commandrex.config.settings.platform_utils.is_macos")
    @patch("commandrex.config.settings.Path.home")
    def test_get_config_dir_macos(
        self, mock_home, mock_is_macos, mock_is_windows, mock_makedirs
    ):
        """Test macOS configuration directory."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True
        mock_home.return_value = Path("/Users/test")

        settings = Settings()
        config_dir = settings._get_config_dir()

        expected = (
            Path("/Users/test") / "Library" / "Application Support" / "CommandRex"
        )
        assert config_dir == expected

    @patch("commandrex.config.settings.os.makedirs")
    @patch("commandrex.config.settings.platform_utils.is_windows")
    @patch("commandrex.config.settings.platform_utils.is_macos")
    @patch("commandrex.config.settings.os.environ.get")
    @patch("commandrex.config.settings.Path.home")
    def test_get_config_dir_linux_with_xdg(
        self, mock_home, mock_env_get, mock_is_macos, mock_is_windows, mock_makedirs
    ):
        """Test Linux configuration directory with XDG_CONFIG_HOME."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_env_get.return_value = "/home/test/.config"

        settings = Settings()
        config_dir = settings._get_config_dir()

        assert config_dir == Path("/home/test/.config") / "commandrex"
        mock_env_get.assert_called_with("XDG_CONFIG_HOME")

    @patch("commandrex.config.settings.os.makedirs")
    @patch("commandrex.config.settings.platform_utils.is_windows")
    @patch("commandrex.config.settings.platform_utils.is_macos")
    @patch("commandrex.config.settings.os.environ.get")
    @patch("commandrex.config.settings.Path.home")
    def test_get_config_dir_linux_without_xdg(
        self, mock_home, mock_env_get, mock_is_macos, mock_is_windows, mock_makedirs
    ):
        """Test Linux configuration directory without XDG_CONFIG_HOME."""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        mock_env_get.return_value = None
        mock_home.return_value = Path("/home/test")

        settings = Settings()
        config_dir = settings._get_config_dir()

        expected = Path("/home/test") / ".config" / "commandrex"
        assert config_dir == expected


class TestSettingsLoadSave:
    """Test settings loading and saving."""

    def test_load_settings_success(self, isolated_settings):
        """Test successful settings loading."""
        test_settings = {
            "api": {"model": "gpt-3.5-turbo", "temperature": 0.5},
            "ui": {"theme": "light"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_settings, f)
            temp_file = f.name

        try:
            settings = isolated_settings
            settings.config_file = Path(temp_file)

            result = settings.load()

            assert result is True
            assert settings.settings["api"]["model"] == "gpt-3.5-turbo"
            assert settings.settings["api"]["temperature"] == 0.5
            assert settings.settings["ui"]["theme"] == "light"
            # Default values should still be present for unspecified settings
            assert settings.settings["api"]["max_tokens"] == 1000  # Default value
        finally:
            os.unlink(temp_file)

    def test_load_settings_file_not_found(self, isolated_settings):
        """Test loading settings when file doesn't exist."""
        settings = isolated_settings
        settings.config_file = Path("/nonexistent/file.json")

        result = settings.load()

        assert result is False
        # Should still have default settings
        assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"

    def test_load_settings_invalid_json(self, isolated_settings):
        """Test loading settings with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            settings = isolated_settings
            settings.config_file = Path(temp_file)

            result = settings.load()

            assert result is False
            # Should still have default settings
            assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"
        finally:
            os.unlink(temp_file)

    def test_save_settings_success(self, isolated_settings):
        """Test successful settings saving."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            settings = isolated_settings
            settings.config_file = Path(temp_file)
            settings.settings["api"]["model"] = "custom-model"

            result = settings.save()

            assert result is True

            # Verify the file was written correctly
            with open(temp_file, "r") as f:
                saved_data = json.load(f)

            assert saved_data["api"]["model"] == "custom-model"
        finally:
            os.unlink(temp_file)

    def test_save_settings_io_error(self, isolated_settings):
        """Test saving settings with IO error."""
        settings = isolated_settings
        settings.config_file = Path("/invalid/path/settings.json")

        result = settings.save()

        assert result is False


class TestSettingsAccess:
    """Test settings access methods."""

    def test_get_setting_existing(self, isolated_settings):
        """Test getting an existing setting."""
        settings = isolated_settings

        value = settings.get("api", "model")
        assert value == "gpt-4.1-mini-2025-04-14"

        value = settings.get("ui", "theme")
        assert value == "dark"

    def test_get_setting_with_default(self, isolated_settings):
        """Test getting a non-existing setting with default."""
        settings = isolated_settings

        value = settings.get("nonexistent", "key", "default_value")
        assert value == "default_value"

        value = settings.get("api", "nonexistent_key", 42)
        assert value == 42

    def test_get_setting_without_default(self, isolated_settings):
        """Test getting a non-existing setting without default."""
        settings = isolated_settings

        value = settings.get("nonexistent", "key")
        assert value is None

    def test_set_setting_existing_section(self, isolated_settings):
        """Test setting a value in an existing section."""
        settings = isolated_settings

        result = settings.set("api", "model", "new-model")
        assert result is True
        assert settings.settings["api"]["model"] == "new-model"

    def test_set_setting_new_section(self, isolated_settings):
        """Test setting a value in a new section."""
        settings = isolated_settings

        result = settings.set("new_section", "new_key", "new_value")
        assert result is True
        assert settings.settings["new_section"]["new_key"] == "new_value"

    def test_set_setting_error(self, isolated_settings):
        """Test setting a value with error."""
        settings = isolated_settings

        # Create a mock that raises an exception when accessed
        mock_settings = MagicMock()
        mock_settings.__getitem__.side_effect = Exception("Test error")

        with patch.object(settings, "settings", mock_settings):
            result = settings.set("api", "model", "new-model")
            assert result is False

    def test_get_all_settings(self, isolated_settings):
        """Test getting all settings."""
        settings = isolated_settings

        all_settings = settings.get_all()

        assert isinstance(all_settings, dict)
        assert "api" in all_settings
        assert "ui" in all_settings
        assert all_settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"

        # Verify it's a copy, not the original
        all_settings["api"]["model"] = "modified"
        assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"


class TestSettingsReset:
    """Test settings reset functionality."""

    def test_reset_to_defaults(self, isolated_settings):
        """Test resetting all settings to defaults."""
        settings = isolated_settings

        # Modify some settings
        settings.set("api", "model", "custom-model")
        settings.set("ui", "theme", "custom-theme")

        # Reset to defaults
        settings.reset_to_defaults()

        # Verify settings are back to defaults
        assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"
        assert settings.settings["ui"]["theme"] == "dark"

    def test_reset_section_existing(self, isolated_settings):
        """Test resetting an existing section."""
        settings = isolated_settings

        # Modify API settings
        settings.set("api", "model", "custom-model")
        settings.set("api", "temperature", 0.8)

        # Reset API section
        result = settings.reset_section("api")

        assert result is True
        assert settings.settings["api"]["model"] == "gpt-4.1-mini-2025-04-14"
        assert settings.settings["api"]["temperature"] == 0.2

    def test_reset_section_nonexistent(self, isolated_settings):
        """Test resetting a non-existent section."""
        settings = isolated_settings

        result = settings.reset_section("nonexistent_section")

        assert result is False


class TestFilePathUtilities:
    """Test file path utility methods."""

    def test_get_history_file_path_custom(self, isolated_settings):
        """Test getting history file path with custom setting."""
        settings = isolated_settings
        settings.set("commands", "history_file", "/custom/path/history.json")

        path = settings.get_history_file_path()

        assert path == Path("/custom/path/history.json")

    def test_get_history_file_path_default(self, isolated_settings):
        """Test getting history file path with default."""
        settings = isolated_settings

        path = settings.get_history_file_path()

        assert path == settings.config_dir / "command_history.json"

    def test_get_log_file_path_custom(self, isolated_settings):
        """Test getting log file path with custom setting."""
        settings = isolated_settings
        settings.set("advanced", "log_file", "/custom/path/app.log")

        path = settings.get_log_file_path()

        assert path == Path("/custom/path/app.log")

    def test_get_log_file_path_debug_mode(self, isolated_settings):
        """Test getting log file path in debug mode."""
        settings = isolated_settings
        settings.set("advanced", "debug_mode", True)

        path = settings.get_log_file_path()

        assert path == settings.config_dir / "commandrex.log"

    def test_get_log_file_path_none(self, isolated_settings):
        """Test getting log file path when not set and not in debug mode."""
        settings = isolated_settings
        settings.set("advanced", "debug_mode", False)
        settings.set("advanced", "log_file", "")

        path = settings.get_log_file_path()

        assert path is None


class TestSecuritySettings:
    """Test security-related settings methods."""

    def test_is_dangerous_command_allowed_sudo_allowed(self, isolated_settings):
        """Test sudo command allowed."""
        settings = isolated_settings
        settings.set("security", "allow_sudo", True)

        result = settings.is_dangerous_command_allowed("sudo")

        assert result is True

    def test_is_dangerous_command_allowed_sudo_denied(self, isolated_settings):
        """Test sudo command denied."""
        settings = isolated_settings
        settings.set("security", "allow_sudo", False)

        result = settings.is_dangerous_command_allowed("sudo")

        assert result is False

    def test_is_dangerous_command_allowed_network_allowed(self, isolated_settings):
        """Test network command allowed."""
        settings = isolated_settings
        settings.set("security", "allow_network", True)

        result = settings.is_dangerous_command_allowed("network")

        assert result is True

    def test_is_dangerous_command_allowed_network_denied(self, isolated_settings):
        """Test network command denied."""
        settings = isolated_settings
        settings.set("security", "allow_network", False)

        result = settings.is_dangerous_command_allowed("network")

        assert result is False

    def test_is_dangerous_command_allowed_file_operations_allowed(
        self, isolated_settings
    ):
        """Test file operations allowed."""
        settings = isolated_settings
        settings.set("security", "allow_file_operations", True)

        result = settings.is_dangerous_command_allowed("file_operations")

        assert result is True

    def test_is_dangerous_command_allowed_file_operations_denied(
        self, isolated_settings
    ):
        """Test file operations denied."""
        settings = isolated_settings
        settings.set("security", "allow_file_operations", False)

        result = settings.is_dangerous_command_allowed("file_operations")

        assert result is False

    def test_is_dangerous_command_allowed_unknown_type(self, isolated_settings):
        """Test unknown command type."""
        settings = isolated_settings

        result = settings.is_dangerous_command_allowed("unknown_type")

        assert result is False

    def test_requires_confirmation_dangerous_command(self, isolated_settings):
        """Test confirmation required for dangerous command."""
        settings = isolated_settings
        settings.set("security", "dangerous_commands_require_confirmation", True)

        result = settings.requires_confirmation(is_dangerous=True)

        assert result is True

    def test_requires_confirmation_dangerous_command_disabled(self, isolated_settings):
        """Test confirmation not required when disabled."""
        settings = isolated_settings
        settings.set("security", "dangerous_commands_require_confirmation", False)

        result = settings.requires_confirmation(is_dangerous=True)

        assert result is False

    def test_requires_confirmation_safe_command(self, isolated_settings):
        """Test confirmation not required for safe command."""
        settings = isolated_settings

        result = settings.requires_confirmation(is_dangerous=False)

        assert result is False


class TestNestedDictUpdate:
    """Test nested dictionary update functionality."""

    def test_update_nested_dict_simple(self, isolated_settings):
        """Test updating nested dictionary with simple values."""
        settings = isolated_settings

        target = {"a": 1, "b": {"c": 2, "d": 3}}
        source = {"b": {"c": 20}}

        settings._update_nested_dict(target, source)

        assert target["a"] == 1
        assert target["b"]["c"] == 20
        assert target["b"]["d"] == 3

    def test_update_nested_dict_new_keys(self, isolated_settings):
        """Test updating nested dictionary with new keys."""
        settings = isolated_settings

        target = {"a": 1}
        source = {"b": {"c": 2}, "d": 3}

        settings._update_nested_dict(target, source)

        assert target["a"] == 1
        assert target["b"]["c"] == 2
        assert target["d"] == 3

    def test_update_nested_dict_overwrite_non_dict(self, isolated_settings):
        """Test updating nested dictionary overwrites non-dict values."""
        settings = isolated_settings

        target = {"a": {"b": 1}}
        source = {"a": "string_value"}

        settings._update_nested_dict(target, source)

        assert target["a"] == "string_value"


class TestSettingsIntegration:
    """Integration tests for settings functionality."""

    @patch("commandrex.config.settings.os.makedirs")
    def test_settings_initialization_creates_config_dir(self, mock_makedirs):
        """Test that settings initialization creates config directory."""
        settings = Settings()

        mock_makedirs.assert_called_once_with(settings.config_dir, exist_ok=True)

    def test_settings_full_workflow(self):
        """Test complete settings workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create settings with temporary config directory
            with patch("commandrex.config.settings.os.makedirs"):
                settings = Settings()
                settings.config_dir = Path(temp_dir)
                settings.config_file = settings.config_dir / "settings.json"
                settings.settings = settings.DEFAULT_SETTINGS.copy()

                # Modify some settings
                settings.set("api", "model", "test-model")
                settings.set("ui", "theme", "custom")

                # Save settings
                result = settings.save()
                assert result is True

                # Create new settings instance and load
                new_settings = Settings()
                new_settings.config_dir = Path(temp_dir)
                new_settings.config_file = new_settings.config_dir / "settings.json"
                new_settings.settings = new_settings.DEFAULT_SETTINGS.copy()

                load_result = new_settings.load()
                assert load_result is True

                # Verify loaded settings
                assert new_settings.get("api", "model") == "test-model"
                assert new_settings.get("ui", "theme") == "custom"
                # Default values should still be present
                assert new_settings.get("api", "temperature") == 0.2


class TestGlobalSettingsInstance:
    """Test the global settings instance."""

    def test_global_settings_import(self):
        """Test that global settings instance can be imported."""
        from commandrex.config.settings import settings

        assert isinstance(settings, Settings)
        # Note: We can't test the exact model value since it may have been
        # modified by other tests
        assert "api" in settings.settings
        assert "model" in settings.settings["api"]
