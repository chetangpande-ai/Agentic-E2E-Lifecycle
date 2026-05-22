"""
Structured logging utility with Rich formatting.
"""

import logging
import sys
from rich.logging import RichHandler
from rich.console import Console
from config.settings import get_settings

console = Console()


def setup_logger(name: str = "agentic_qe") -> logging.Logger:
    """Create a configured logger with Rich formatting."""
    settings = get_settings()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if not logger.handlers:
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(rich_handler)

    return logger


# Default logger instance
logger = setup_logger()
