# src/log_utils.py
"""
log_utils.py
============

Utility functions for standardized, color‑coded logging with optional verbosity control.

This module provides simple logging helpers (`info`, `warn`, `error`) that print
timestamped messages to the console, with color formatting via `colorama` for
improved readability. It also includes a global verbosity flag to control whether
informational messages are displayed.

Features
--------
- **Timestamped Output**:
  All log messages include the current local time in `YYYY-MM-DD HH:MM:SS` format.

- **Color‑Coded Levels**:
  - INFO → Green
  - WARN → Yellow
  - ERROR → Red

- **Verbosity Control**:
  - `set_verbose(True)` enables INFO messages.
  - WARN and ERROR messages are always shown.

Functions
---------
- `set_verbose(value: bool) -> None`  
  Enable or disable INFO‑level logging globally.

- `info(msg: str) -> None`  
  Print a green INFO message if verbosity is enabled.

- `warn(msg: str) -> None`  
  Print a yellow WARN message (always shown).

- `error(msg: str) -> None`  
  Print a red ERROR message (always shown).

Dependencies
------------
- `colorama` for cross‑platform colored terminal output.
- `datetime` from the Python standard library.

Usage Example
-------------
    from log_utils import set_verbose, info, warn, error

    set_verbose(True)
    info("Data fetch started.")
    warn("API rate limit approaching.")
    error("Failed to retrieve market data.")

Notes
-----
Call `set_verbose(True)` early in your application if you want INFO messages
to be visible. On Windows, `colorama.init(autoreset=True)` ensures colors reset
automatically after each message.
"""

from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama (needed for Windows)
init(autoreset=True)

# Global verbosity flag
_VERBOSE = False

def set_verbose(value: bool) -> None:
    """Set global verbosity for logging."""
    global _VERBOSE
    _VERBOSE = value

def _ts() -> str:
    """Return current timestamp as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def info(msg: str) -> None:
    if _VERBOSE:
        print(f"{Fore.GREEN}[{_ts()}][INFO]{Style.RESET_ALL} {msg}")

def warn(msg: str) -> None:
    # Warnings always show
    print(f"{Fore.YELLOW}[{_ts()}][WARN]{Style.RESET_ALL} {msg}")

def error(msg: str) -> None:
    # Errors always show
    print(f"{Fore.RED}[{_ts()}][ERROR]{Style.RESET_ALL} {msg}")


