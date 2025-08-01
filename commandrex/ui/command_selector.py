from __future__ import annotations

import sys
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from commandrex.models.command_models import CommandOption


class InteractiveCommandSelector:
    """
    Render a list of CommandOption entries and allow the user to pick one
    using arrow keys (Up/Down) and Enter. Press 'q' or ESC to cancel and return None.
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.index = 0

    def _build_table(self, options: List[CommandOption]) -> Table:
        table = Table(
            title="Suggested Commands",
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Command", style="bold white")
        table.add_column("Explanation", style="white")
        for i, opt in enumerate(options):
            selector = "➤" if i == self.index else " "
            cmd_text = Text(opt.command)
            if i == self.index:
                cmd_text.stylize("bold white on blue")
            table.add_row(
                selector,
                cmd_text,
                opt.description,
            )
        return table

    # Details panel removed for simplicity

    def _render(self, options: List[CommandOption]) -> Panel:
        if not options:
            return Panel("No options to display", border_style="red")
        table = self._build_table(options)
        return Panel(
            table,
            title="Select a command (↑/↓ to navigate, Enter to select, q to cancel)",
        )

    def _read_key(self) -> str:
        """
        Minimal cross-platform key reader.
        Windows: use msvcrt
        Unix: stdin raw mode fallback with arrow escape sequences.
        """
        if sys.platform.startswith("win"):
            try:
                import msvcrt  # type: ignore

                while True:
                    ch = msvcrt.getch()
                    # Arrow keys are two-byte sequences: b'\xe0' then code
                    if ch in (b"\x00", b"\xe0"):
                        code = msvcrt.getch()
                        if code == b"H":
                            return "UP"
                        if code == b"P":
                            return "DOWN"
                        # ignore LEFT/RIGHT for now
                        continue
                    if ch == b"\r":
                        return "ENTER"
                    if ch in (b"q", b"Q"):
                        return "QUIT"
                    if ch == b"\x1b":  # ESC
                        return "QUIT"
                    # ignore other keys
            except Exception:
                # Fallback to ENTER-only selection
                return "ENTER"
        else:
            # Unix-like: read raw bytes and parse escape sequences
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":  # ESC or start of CSI
                        seq1 = sys.stdin.read(1)
                        if seq1 == "[":
                            seq2 = sys.stdin.read(1)
                            if seq2 == "A":
                                return "UP"
                            if seq2 == "B":
                                return "DOWN"
                            # ignore left/right
                        else:
                            return "QUIT"
                    elif ch == "\r" or ch == "\n":
                        return "ENTER"
                    elif ch in ("q", "Q"):
                        return "QUIT"
                    # ignore others
            except Exception:
                return "ENTER"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def select(self, options: List[CommandOption]) -> Optional[CommandOption]:
        """
        Run the interactive selector and return the chosen CommandOption
        or None if cancelled.
        """
        if not options:
            return None

        with Live(
            self._render(options), refresh_per_second=30, console=self.console
        ) as live:
            while True:
                key = self._read_key()
                if key == "UP":
                    self.index = (self.index - 1) % len(options)
                    live.update(self._render(options))
                elif key == "DOWN":
                    self.index = (self.index + 1) % len(options)
                    live.update(self._render(options))
                elif key == "ENTER":
                    return options[self.index]
                elif key == "QUIT":
                    return None
