"""
Unit tests for commandrex.utils.logging module.

This module tests the logging utilities including custom formatters,
logger setup, and configuration management.
"""

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from commandrex.utils.logging import (
    LogFormatter,
    get_logger,
    initialize_logging,
    setup_logging,
)


class TestLogFormatter:
    """Test cases for LogFormatter class."""

    def test_formatter_initialization_with_colors(self):
        """Test LogFormatter initialization with colors enabled."""
        formatter = LogFormatter(use_colors=True)
        assert formatter.use_colors is True
        assert formatter._fmt == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"

    def test_formatter_initialization_without_colors(self):
        """Test LogFormatter initialization with colors disabled."""
        formatter = LogFormatter(use_colors=False)
        assert formatter.use_colors is False
        assert formatter._fmt == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"

    def test_formatter_default_initialization(self):
        """Test LogFormatter default initialization."""
        formatter = LogFormatter()
        assert formatter.use_colors is True

    def test_color_constants(self):
        """Test that color constants are properly defined."""
        formatter = LogFormatter()
        expected_colors = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[35m",  # Magenta
            "RESET": "\033[0m",  # Reset
        }
        assert formatter.COLORS == expected_colors

    def test_format_with_colors_debug(self):
        """Test formatting DEBUG level with colors."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[36m" in formatted  # Cyan color for DEBUG
        assert "\033[0m" in formatted  # Reset color
        assert "DEBUG" in formatted
        assert "Test message" in formatted
        # Verify original levelname is restored
        assert record.levelname == "DEBUG"

    def test_format_with_colors_info(self):
        """Test formatting INFO level with colors."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Info message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[32m" in formatted  # Green color for INFO
        assert "\033[0m" in formatted  # Reset color
        assert "INFO" in formatted
        assert "Info message" in formatted

    def test_format_with_colors_warning(self):
        """Test formatting WARNING level with colors."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[33m" in formatted  # Yellow color for WARNING
        assert "\033[0m" in formatted  # Reset color
        assert "WARNING" in formatted
        assert "Warning message" in formatted

    def test_format_with_colors_error(self):
        """Test formatting ERROR level with colors."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[31m" in formatted  # Red color for ERROR
        assert "\033[0m" in formatted  # Reset color
        assert "ERROR" in formatted
        assert "Error message" in formatted

    def test_format_with_colors_critical(self):
        """Test formatting CRITICAL level with colors."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="",
            lineno=0,
            msg="Critical message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[35m" in formatted  # Magenta color for CRITICAL
        assert "\033[0m" in formatted  # Reset color
        assert "CRITICAL" in formatted
        assert "Critical message" in formatted

    def test_format_without_colors(self):
        """Test formatting without colors."""
        formatter = LogFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[" not in formatted  # No ANSI codes
        assert "INFO" in formatted
        assert "Test message" in formatted

    def test_format_unknown_level_with_colors(self):
        """Test formatting unknown level with colors enabled."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=25,  # Custom level
            pathname="",
            lineno=0,
            msg="Custom message",
            args=(),
            exc_info=None,
        )
        record.levelname = "CUSTOM"

        formatted = formatter.format(record)
        # Should not add colors for unknown levels
        assert "\033[" not in formatted or formatted.count("\033[") == 0
        assert "CUSTOM" in formatted
        assert "Custom message" in formatted

    def test_format_preserves_original_levelname(self):
        """Test that formatting preserves the original levelname."""
        formatter = LogFormatter(use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        original_levelname = record.levelname
        formatter.format(record)
        assert record.levelname == original_levelname


class TestSetupLogging:
    """Test cases for setup_logging function."""

    def teardown_method(self):
        """Clean up after each test."""
        # Clear all handlers from commandrex logger
        logger = logging.getLogger("commandrex")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_basic(self, mock_supports_colors):
        """Test basic logging setup."""
        mock_supports_colors.return_value = True

        logger = setup_logging()

        assert logger.name == "commandrex"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_debug_level(self, mock_supports_colors):
        """Test logging setup with DEBUG level."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="DEBUG")

        assert logger.level == logging.DEBUG
        assert logger.handlers[0].level == logging.DEBUG

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_warning_level(self, mock_supports_colors):
        """Test logging setup with WARNING level."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="WARNING")

        assert logger.level == logging.WARNING
        assert logger.handlers[0].level == logging.WARNING

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_error_level(self, mock_supports_colors):
        """Test logging setup with ERROR level."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="ERROR")

        assert logger.level == logging.ERROR
        assert logger.handlers[0].level == logging.ERROR

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_critical_level(self, mock_supports_colors):
        """Test logging setup with CRITICAL level."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="CRITICAL")

        assert logger.level == logging.CRITICAL
        assert logger.handlers[0].level == logging.CRITICAL

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_invalid_level(self, mock_supports_colors):
        """Test logging setup with invalid level defaults to INFO."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="INVALID")

        assert logger.level == logging.INFO

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_with_lowercase_level(self, mock_supports_colors):
        """Test logging setup with lowercase level."""
        mock_supports_colors.return_value = True

        logger = setup_logging(log_level="debug")

        assert logger.level == logging.DEBUG

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_colors_enabled_platform_supports(self, mock_supports_colors):
        """Test logging setup with colors when platform supports them."""
        mock_supports_colors.return_value = True

        logger = setup_logging(use_colors=True)

        formatter = logger.handlers[0].formatter
        assert isinstance(formatter, LogFormatter)
        assert formatter.use_colors is True

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_colors_enabled_platform_no_support(
        self, mock_supports_colors
    ):
        """Test logging setup with colors when platform doesn't support them."""
        mock_supports_colors.return_value = False

        logger = setup_logging(use_colors=True)

        formatter = logger.handlers[0].formatter
        assert isinstance(formatter, LogFormatter)
        assert formatter.use_colors is False

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_colors_disabled(self, mock_supports_colors):
        """Test logging setup with colors disabled."""
        mock_supports_colors.return_value = True

        logger = setup_logging(use_colors=False)

        formatter = logger.handlers[0].formatter
        assert isinstance(formatter, LogFormatter)
        assert formatter.use_colors is False

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    @patch("os.makedirs")
    def test_setup_logging_with_file(self, mock_makedirs, mock_supports_colors):
        """Test logging setup with file output."""
        mock_supports_colors.return_value = True

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            logger = setup_logging(log_file=log_file)

            try:
                assert len(logger.handlers) == 2
                # Console handler
                assert isinstance(logger.handlers[0], logging.StreamHandler)
                # File handler
                assert isinstance(logger.handlers[1], logging.FileHandler)

                # Check file handler properties
                file_handler = logger.handlers[1]
                assert file_handler.baseFilename == str(log_file)
                assert isinstance(file_handler.formatter, LogFormatter)
                assert file_handler.formatter.use_colors is False
            finally:
                # Close file handlers to avoid permission errors on Windows
                for handler in logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    @patch("os.makedirs")
    def test_setup_logging_with_file_string_path(
        self, mock_makedirs, mock_supports_colors
    ):
        """Test logging setup with file output as string path."""
        mock_supports_colors.return_value = True

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = str(Path(temp_dir) / "test.log")

            logger = setup_logging(log_file=log_file)

            try:
                assert len(logger.handlers) == 2
                file_handler = logger.handlers[1]
                assert file_handler.baseFilename == log_file
            finally:
                # Close file handlers to avoid permission errors on Windows
                for handler in logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_clears_existing_handlers(self, mock_supports_colors):
        """Test that setup_logging clears existing handlers."""
        mock_supports_colors.return_value = True

        # Set up initial logger with handler
        initial_logger = logging.getLogger("commandrex")
        initial_handler = logging.StreamHandler()
        initial_logger.addHandler(initial_handler)

        assert len(initial_logger.handlers) == 1

        # Setup logging again
        logger = setup_logging()

        # Should have cleared old handler and added new one
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is not initial_handler

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_console_handler_uses_stdout(self, mock_supports_colors):
        """Test that console handler uses stdout."""
        mock_supports_colors.return_value = True

        logger = setup_logging()

        console_handler = logger.handlers[0]
        assert console_handler.stream is sys.stdout


class TestGetLogger:
    """Test cases for get_logger function."""

    def test_get_logger_with_name(self):
        """Test getting logger with specific name."""
        logger = get_logger("test_module")

        assert logger.name == "commandrex.test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_without_name(self):
        """Test getting logger without name."""
        logger = get_logger()

        assert logger.name == "commandrex"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_none_name(self):
        """Test getting logger with None name."""
        logger = get_logger(None)

        assert logger.name == "commandrex"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_empty_string(self):
        """Test getting logger with empty string name."""
        logger = get_logger("")

        assert logger.name == "commandrex"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_multiple_calls_same_name(self):
        """Test that multiple calls with same name return same logger."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2
        assert logger1.name == "commandrex.same_module"

    def test_get_logger_different_names(self):
        """Test that different names return different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name == "commandrex.module1"
        assert logger2.name == "commandrex.module2"


class TestInitializeLogging:
    """Test cases for initialize_logging function."""

    def teardown_method(self):
        """Clean up after each test."""
        # Clear all handlers from commandrex logger
        logger = logging.getLogger("commandrex")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("commandrex.utils.logging.settings")
    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_initialize_logging_default_settings(
        self, mock_supports_colors, mock_settings
    ):
        """Test initialize_logging with default settings."""
        mock_supports_colors.return_value = True
        mock_settings.get.return_value = "INFO"
        mock_settings.get_log_file_path.return_value = None

        logger = initialize_logging()

        assert logger.name == "commandrex"
        assert logger.level == logging.INFO
        mock_settings.get.assert_called_once_with("advanced", "log_level", "INFO")
        mock_settings.get_log_file_path.assert_called_once()

    @patch("commandrex.utils.logging.settings")
    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_initialize_logging_debug_level(self, mock_supports_colors, mock_settings):
        """Test initialize_logging with DEBUG level."""
        mock_supports_colors.return_value = True
        mock_settings.get.return_value = "DEBUG"
        mock_settings.get_log_file_path.return_value = None

        logger = initialize_logging()

        assert logger.level == logging.DEBUG

    @patch("commandrex.utils.logging.settings")
    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    @patch("os.makedirs")
    def test_initialize_logging_with_file(
        self, mock_makedirs, mock_supports_colors, mock_settings
    ):
        """Test initialize_logging with log file."""
        mock_supports_colors.return_value = True
        mock_settings.get.return_value = "INFO"

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "app.log"
            mock_settings.get_log_file_path.return_value = log_file

            logger = initialize_logging()

            try:
                assert len(logger.handlers) == 2
                # Should have both console and file handlers
                handler_types = [type(h).__name__ for h in logger.handlers]
                assert "StreamHandler" in handler_types
                assert "FileHandler" in handler_types
            finally:
                # Close file handlers to avoid permission errors on Windows
                for handler in logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)


class TestGlobalLoggerInstance:
    """Test cases for global logger instance."""

    def test_global_logger_exists(self):
        """Test that global logger instance exists."""
        from commandrex.utils.logging import logger

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "commandrex"

    @patch("commandrex.utils.logging.initialize_logging")
    def test_global_logger_is_configured(self, mock_initialize):
        """Test that global logger is properly configured."""
        # Mock the initialize_logging to return a configured logger
        mock_logger = Mock()
        mock_logger.handlers = [Mock()]
        mock_logger.level = logging.INFO
        mock_initialize.return_value = mock_logger

        # Re-import to trigger the mocked initialization
        import importlib

        import commandrex.utils.logging

        importlib.reload(commandrex.utils.logging)

        logger = commandrex.utils.logging.logger

        # Should have at least one handler (console)
        assert len(logger.handlers) >= 1

        # Should have appropriate level set
        assert logger.level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def teardown_method(self):
        """Clean up after each test."""
        # Clear all handlers from commandrex logger
        logger = logging.getLogger("commandrex")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_full_logging_workflow(self, mock_supports_colors):
        """Test complete logging workflow."""
        mock_supports_colors.return_value = True

        # Setup logging
        logger = setup_logging(log_level="DEBUG")

        # Get module-specific logger
        module_logger = get_logger("test_module")

        # Both should be part of the same hierarchy
        assert module_logger.name.startswith(logger.name)

        # Module logger should inherit level from parent
        assert module_logger.getEffectiveLevel() == logging.DEBUG

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_logging_with_file_and_console(self, mock_supports_colors):
        """Test logging to both file and console."""
        mock_supports_colors.return_value = True

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            logger = setup_logging(log_level="INFO", log_file=log_file)

            try:
                # Log a message
                logger.info("Test message")

                # Flush handlers to ensure message is written
                for handler in logger.handlers:
                    handler.flush()

                # Check that file was created and contains the message
                assert log_file.exists()
                content = log_file.read_text(encoding="utf-8")
                assert "Test message" in content
                assert "INFO" in content
            finally:
                # Close file handlers to avoid permission errors on Windows
                for handler in logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_color_formatting_integration(self, mock_supports_colors):
        """Test color formatting integration."""
        mock_supports_colors.return_value = True

        # Capture console output
        from io import StringIO

        captured_output = StringIO()

        # Setup logging with custom stream
        logger = logging.getLogger("test_color")
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add handler with our captured stream
        handler = logging.StreamHandler(captured_output)
        formatter = LogFormatter(use_colors=True)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log messages at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        output = captured_output.getvalue()

        # Check that color codes are present
        assert "\033[36m" in output  # Debug (cyan)
        assert "\033[32m" in output  # Info (green)
        assert "\033[33m" in output  # Warning (yellow)
        assert "\033[31m" in output  # Error (red)
        assert "\033[35m" in output  # Critical (magenta)
        assert "\033[0m" in output  # Reset

        # Check that messages are present
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output
        assert "Critical message" in output


class TestLoggingEdgeCases:
    """Test edge cases and error conditions."""

    def teardown_method(self):
        """Clean up after each test."""
        # Clear all handlers from commandrex logger
        logger = logging.getLogger("commandrex")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    @patch("os.makedirs")
    def test_setup_logging_file_creation_error(
        self, mock_makedirs, mock_supports_colors
    ):
        """Test setup_logging when file creation fails."""
        mock_supports_colors.return_value = True
        mock_makedirs.side_effect = OSError("Permission denied")

        # Should not raise exception, just skip file handler
        with pytest.raises(OSError):
            setup_logging(log_file="/invalid/path/test.log")

    def test_log_formatter_with_exception_info(self):
        """Test LogFormatter with exception information."""
        formatter = LogFormatter(use_colors=True)

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

            formatted = formatter.format(record)
            assert "Error occurred" in formatted
            assert "ValueError: Test exception" in formatted
            assert "Traceback" in formatted

    @patch("commandrex.executor.platform_utils.supports_ansi_colors")
    def test_setup_logging_multiple_calls_cleanup(self, mock_supports_colors):
        """Test that multiple setup_logging calls properly clean up."""
        mock_supports_colors.return_value = True

        # First setup
        logger1 = setup_logging(log_level="DEBUG")
        initial_handler_count = len(logger1.handlers)

        # Second setup
        logger2 = setup_logging(log_level="INFO")

        # Should be same logger instance
        assert logger1 is logger2

        # Should have same number of handlers (old ones cleaned up)
        assert len(logger2.handlers) == initial_handler_count

        # Level should be updated
        assert logger2.level == logging.INFO
