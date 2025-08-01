"""
Logging utilities for CommandRex.

This module provides a structured logging system for the application,
with support for different log levels, file output, and formatting.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union

# Import from our own modules
from commandrex.config.settings import settings


class LogFormatter(logging.Formatter):
    """Custom formatter for logs with color support."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, use_colors: bool = True):
        """
        Initialize the formatter.

        Args:
            use_colors (bool): Whether to use colors in the output.
        """
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with optional colors.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: Formatted log message.
        """
        # Save the original levelname
        original_levelname = record.levelname

        # Apply colors if enabled
        if self.use_colors and record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}{self.COLORS['RESET']}"
            )

        # Format the record
        result = super().format(record)

        # Restore the original levelname
        record.levelname = original_levelname

        return result


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    use_colors: bool = True,
) -> logging.Logger:
    """
    Set up the logging system.

    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file (Optional[Union[str, Path]]): Path to log file.
        use_colors (bool): Whether to use colors in console output.

    Returns:
        logging.Logger: Configured logger.
    """
    # Get the root logger
    logger = logging.getLogger("commandrex")

    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set the log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Determine if we should use colors
    from commandrex.executor import platform_utils

    supports_colors = platform_utils.supports_ansi_colors() and use_colors

    # Create formatters
    console_formatter = LogFormatter(use_colors=supports_colors)
    console_handler.setFormatter(console_formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if log_file:
        # Ensure the directory exists
        log_path = Path(log_file)
        os.makedirs(log_path.parent, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)

        # Use a non-colored formatter for the file
        file_formatter = LogFormatter(use_colors=False)
        file_handler.setFormatter(file_formatter)

        # Add file handler to logger
        logger.addHandler(file_handler)

    # Log the initialization
    logger.debug(f"Logging initialized at level {log_level}")

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name (str): Logger name, relative to the base package.

    Returns:
        logging.Logger: Logger instance.
    """
    if name:
        return logging.getLogger(f"commandrex.{name}")
    else:
        return logging.getLogger("commandrex")


# Initialize logging based on settings
def initialize_logging() -> logging.Logger:
    """
    Initialize logging based on application settings.

    Returns:
        logging.Logger: Configured logger.
    """
    log_level = settings.get("advanced", "log_level", "INFO")
    log_file_path = settings.get_log_file_path()

    return setup_logging(log_level=log_level, log_file=log_file_path, use_colors=True)


# Global logger instance
logger = initialize_logging()
