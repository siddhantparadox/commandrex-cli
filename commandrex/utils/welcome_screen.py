"""
Welcome screen for CommandRex interactive mode.

This module provides a welcome screen with ASCII art that displays
when users enter the interactive mode of CommandRex.
"""

from rich.align import Align
from rich.console import Console
from rich.text import Text

from commandrex.config.settings import settings
from commandrex.executor import platform_utils

# ASCII art constants
COMMAND_ASCII = """
 ██████  ██████  ███    ███ ███    ███  █████  ███    ██ ██████
██      ██    ██ ████  ████ ████  ████ ██   ██ ████   ██ ██   ██
██      ██    ██ ██ ████ ██ ██ ████ ██ ███████ ██ ██  ██ ██   ██
██      ██    ██ ██  ██  ██ ██  ██  ██ ██   ██ ██  ██ ██ ██   ██
 ██████  ██████  ██      ██ ██      ██ ██   ██ ██   ████ ██████
"""

REX_ASCII = """
██████  ███████ ██   ██
██   ██ ██       ██ ██
██████  █████     ███
██   ██ ██       ██ ██
██   ██ ███████ ██   ██
"""


def should_show_welcome() -> bool:
    """
    Check if welcome screen should be displayed.

    Returns:
        bool: True if welcome screen should be shown, False otherwise.
    """
    # Check settings for show_welcome_screen option
    return settings.get("ui", "show_welcome_screen", True)


def display_welcome_screen(console: Console) -> None:
    """
    Display the CommandRex welcome screen.

    Args:
        console (Console): Rich console instance for output.
    """
    if not should_show_welcome():
        return

    # Check if terminal supports colors
    supports_colors = platform_utils.supports_ansi_colors()

    # Create styled text
    if supports_colors:
        header = Text("* Welcome to Command Rex", style="bold green")
        command_text = Text(COMMAND_ASCII, style="bold green")
        rex_text = Text(REX_ASCII, style="bold green")
        continue_text = Text("Press Enter to continue", style="dim green")
    else:
        header = Text("* Welcome to Command Rex")
        command_text = Text(COMMAND_ASCII)
        rex_text = Text(REX_ASCII)
        continue_text = Text("Press Enter to continue")

    # Clear screen for better presentation
    console.clear()

    # Display the welcome screen elements
    console.print()  # Empty line at top
    console.print(Align.center(header))
    console.print()  # Empty line
    console.print(Align.center(command_text))
    console.print(Align.center(rex_text))
    console.print()  # Empty line
    console.print(Align.center(continue_text))

    # Wait for user input
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C or EOF gracefully
        console.print("\n[yellow]Skipping welcome screen...[/]")

    # Clear screen again before entering interactive mode
    console.clear()
