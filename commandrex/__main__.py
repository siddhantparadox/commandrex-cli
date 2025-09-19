"""
Main entry point for running CommandRex as a module.

This allows the package to be executed directly with:
python -m commandrex
"""

from commandrex.main import app


def main() -> None:
    """Run the CommandRex CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
