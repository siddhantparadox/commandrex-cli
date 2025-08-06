import random
import sys
import threading
import time
from typing import Callable, List, Optional


class UniversalCommandRexAnimation:
    """
    Pure ASCII, dependency-free animation that works across all shells
    (CMD, PowerShell, Git Bash, SSH).

    Provides fun, rotating messages while background work is running.
    """

    # Simple ASCII spinners that are universally supported
    SPINNER_FRAMES = ["|", "/", "-", "\\"]

    # ASCII wave/pulse frames (universal)
    WAVE_FRAMES = ["~-~-~-~-~", "-~-~-~-~-", "~-~-~-~-~", "-~-~-~-~-"]
    PULSE_FRAMES = ["(   )", "( . )", "( o )", "( O )", "( o )", "( . )"]

    # Personality-rich messages grouped by stage (expanded)
    FUNNY_MESSAGES: List[List[str]] = [
        # Stage 0: Wake-up
        [
            "waking up neurons",
            "stretching my dino brain",
            "booting up Rex cores",
            "warming up synapses",
            "fueling the thought reactor",
            "aligning command chakras",
            "calibrating roar levels",
        ],
        # Stage 1: Understanding
        [
            "commandrexing your request",
            "decoding human speak",
            "understanding your wishes",
            "parsing intent",
            "reading between the flags",
            "translating vibes to syntax",
            "listening to your terminal dreams",
        ],
        # Stage 2: Searching
        [
            "tinkering with terminals",
            "searching the command cosmos",
            "hunting the right flags",
            "excavating the perfect syntax",
            "combing the man pages",
            "sniffing out parameters",
            "spelunking through options",
        ],
        # Stage 3: Crafting
        [
            "brewing command magic",
            "assembling command blocks",
            "forging terminal poetry",
            "mixing a command cocktail",
            "kneading a dough of arguments",
            "welding pipes and redirects",
            "plating the CLI delicacy",
        ],
        # Stage 4: Finalizing
        [
            "polishing the masterpiece",
            "double-checking parameters",
            "adding final touches",
            "making it perfect for you",
            "buffing the output",
            "tidying up the flags",
            "wrapping it with care",
        ],
    ]

    def __init__(self, use_inline: bool = True, update_interval: float = 0.12) -> None:
        """
        use_inline: if True, writes and rewrites a single line
                    (better for most terminals).
                    if False, prints multiple lines
                    (safer for very basic terminals).

        update_interval: seconds between frame updates.
        """
        self.use_inline = use_inline
        # Slow down default update interval for readability
        self.update_interval = max(0.18, update_interval)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._frame: int = 0
        # Control how long a phrase stays before changing (in seconds)
        self._phrase_hold_seconds: float = 1.2
        self._last_phrase_change: float = 0.0
        self._current_phrase: Optional[str] = None

    def _pick_message(self, elapsed: float) -> str:
        # Choose a stage based on elapsed time (slower stage progression)
        if elapsed < 1.2:
            stage = 0
        elif elapsed < 2.4:
            stage = 1
        elif elapsed < 3.6:
            stage = 2
        elif elapsed < 4.8:
            stage = 3
        else:
            stage = 4

        # Hold the same phrase for a bit so it's readable
        now = time.time()
        if (
            not self._current_phrase
            or (now - self._last_phrase_change) >= self._phrase_hold_seconds
        ):
            self._current_phrase = random.choice(self.FUNNY_MESSAGES[stage])
            self._last_phrase_change = now

        return self._current_phrase

    def _compose_line(self, elapsed: float) -> str:
        spin = self.SPINNER_FRAMES[self._frame % len(self.SPINNER_FRAMES)]
        wave = self.WAVE_FRAMES[self._frame % len(self.WAVE_FRAMES)]
        pulse = self.PULSE_FRAMES[self._frame % len(self.PULSE_FRAMES)]

        # Slow the dots cycle to avoid jitter
        dots_count = ((self._frame // 2) % 3) + 1
        dots = "." * dots_count
        msg = self._pick_message(elapsed)

        # Single line, concise, safe across terminals
        return f"{spin} {wave} CommandRex is {msg}{dots} {pulse}"

    def _compose_block(self, elapsed: float) -> str:
        # Multi-line block version (no ANSI control codes)
        wave = self.WAVE_FRAMES[self._frame % len(self.WAVE_FRAMES)]
        pulse = self.PULSE_FRAMES[self._frame % len(self.PULSE_FRAMES)]
        dots = "." * (((self._frame // 2) % 3) + 1)
        msg = self._pick_message(elapsed)

        bar_width = 28
        # Slow the assumed total duration for a smoother progress bar
        progress = min(elapsed / 6.0, 1.0)
        filled = int(progress * bar_width)
        bar = "[" + "=" * filled + ">" + " " * (bar_width - filled - 1) + "]"
        pct = f"{int(progress * 100):3d}%"

        lines = [
            "  " + "=" * 42,
            f"   CommandRex is {msg}{dots}",
            "  " + "-" * 42,
            f"     {wave}",
            f"     {bar} {pct}",
            f"     {pulse}",
            "  " + "=" * 42,
        ]
        return "\n".join(lines)

    def _run(self) -> None:
        self._start_time = time.time()
        self._last_phrase_change = self._start_time
        # For very basic shells, avoid carriage returns and complex cursor moves.
        inline_supported = self.use_inline and sys.stdout.isatty()

        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            output = (
                self._compose_line(elapsed)
                if inline_supported
                else self._compose_block(elapsed)
            )

            if inline_supported:
                # Print inline with carriage return, no ANSI sequences required
                sys.stdout.write("\r" + output + " " * 8)
                sys.stdout.flush()
            else:
                # Print a block, separated by a blank line; do not attempt to
                # erase the previous block for maximum compatibility
                print(output)
            time.sleep(self.update_interval)
            self._frame += 1

        # On stop, tidy up line if inline
        if inline_supported:
            sys.stdout.write("\r" + " " * 120 + "\r")
            sys.stdout.flush()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None


class AnimationRunner:
    """
    Helper to run the UniversalCommandRexAnimation while a callable
    (sync/async) executes.
    """

    def __init__(self, use_inline: bool = True, update_interval: float = 0.12) -> None:
        # Default to a slower, more readable cadence
        effective_interval = max(0.18, update_interval)
        self.animation = UniversalCommandRexAnimation(
            use_inline=use_inline, update_interval=effective_interval
        )

    def run_sync(self, fn: Callable[[], object]) -> object:
        """
        Run a synchronous function while showing the animation.
        """
        self.animation.start()
        try:
            return fn()
        finally:
            self.animation.stop()

    async def run_async(self, coro_fn: Callable[[], object]) -> object:
        """
        Run an async coroutine while showing the animation.
        coro_fn should be an awaitable callable (e.g., lambda: client.call(...))
        """
        import asyncio

        self.animation.start()
        try:
            return await coro_fn()
        finally:
            # Give a tiny delay to ensure last frame clears, then stop
            await asyncio.sleep(0.02)
            self.animation.stop()
