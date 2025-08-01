"""
Unit tests for the welcome screen module.
"""

from unittest.mock import Mock, patch

from rich.console import Console

from commandrex.utils.welcome_screen import (
    COMMAND_ASCII,
    REX_ASCII,
    display_welcome_screen,
    should_show_welcome,
)


class TestWelcomeScreen:
    """Test cases for welcome screen functionality."""

    def test_should_show_welcome_default(self):
        """Test that welcome screen is shown by default."""
        with patch("commandrex.utils.welcome_screen.settings") as mock_settings:
            mock_settings.get.return_value = True
            assert should_show_welcome() is True

    def test_should_show_welcome_disabled(self):
        """Test that welcome screen can be disabled."""
        with patch("commandrex.utils.welcome_screen.settings") as mock_settings:
            mock_settings.get.return_value = False
            assert should_show_welcome() is False

    def test_ascii_art_constants(self):
        """Test that ASCII art constants are defined."""
        assert isinstance(COMMAND_ASCII, str)
        assert isinstance(REX_ASCII, str)
        assert len(COMMAND_ASCII.strip()) > 0
        assert len(REX_ASCII.strip()) > 0

    @patch("commandrex.utils.welcome_screen.should_show_welcome")
    @patch("commandrex.utils.welcome_screen.platform_utils.supports_ansi_colors")
    @patch("builtins.input")
    def test_display_welcome_screen_with_colors(
        self, mock_input, mock_supports_colors, mock_should_show
    ):
        """Test welcome screen display with color support."""
        mock_should_show.return_value = True
        mock_supports_colors.return_value = True
        mock_input.return_value = ""

        console = Mock(spec=Console)
        display_welcome_screen(console)

        # Verify console methods were called
        console.clear.assert_called()
        assert console.print.call_count >= 4  # Header, command, rex, continue text

    @patch("commandrex.utils.welcome_screen.should_show_welcome")
    @patch("commandrex.utils.welcome_screen.platform_utils.supports_ansi_colors")
    @patch("builtins.input")
    def test_display_welcome_screen_without_colors(
        self, mock_input, mock_supports_colors, mock_should_show
    ):
        """Test welcome screen display without color support."""
        mock_should_show.return_value = True
        mock_supports_colors.return_value = False
        mock_input.return_value = ""

        console = Mock(spec=Console)
        display_welcome_screen(console)

        # Verify console methods were called
        console.clear.assert_called()
        assert console.print.call_count >= 4

    @patch("commandrex.utils.welcome_screen.should_show_welcome")
    def test_display_welcome_screen_disabled(self, mock_should_show):
        """Test that welcome screen is not displayed when disabled."""
        mock_should_show.return_value = False

        console = Mock(spec=Console)
        display_welcome_screen(console)

        # Verify console methods were not called
        console.clear.assert_not_called()
        console.print.assert_not_called()

    @patch("commandrex.utils.welcome_screen.should_show_welcome")
    @patch("commandrex.utils.welcome_screen.platform_utils.supports_ansi_colors")
    @patch("builtins.input")
    def test_display_welcome_screen_keyboard_interrupt(
        self, mock_input, mock_supports_colors, mock_should_show
    ):
        """Test welcome screen handles keyboard interrupt gracefully."""
        mock_should_show.return_value = True
        mock_supports_colors.return_value = True
        mock_input.side_effect = KeyboardInterrupt()

        console = Mock(spec=Console)

        # Should not raise exception
        display_welcome_screen(console)

        # Verify console methods were called
        console.clear.assert_called()
        assert console.print.call_count >= 5  # Includes the "Skipping..." message
