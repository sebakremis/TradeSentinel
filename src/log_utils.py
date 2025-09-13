# src/log_utils.py
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


