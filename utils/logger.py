"""
Structured logging utility with Rich formatting, file logging, and debugging.
Provides centralized logging with console and file outputs for analysis.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console
from config.settings import get_settings

console = Console()

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(name: str = "agentic_qe", log_to_file: bool = True) -> logging.Logger:
    """
    Create a configured logger with Rich formatting, console, and file outputs.
    
    Args:
        name: Logger name (typically module name)
        log_to_file: Whether to also log to file for analysis
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    # Avoid duplicate handlers
    if not logger.handlers:
        # Rich console handler
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(rich_handler)

        # File handler for debugging and analysis
        if log_to_file:
            log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get or create a logger with optional file logging."""
    if name is None:
        name = "agentic_qe"
    return setup_logger(name)


def log_execution_start(logger: logging.Logger, component: str, details: dict = None):
    """Log the start of execution with component details."""
    msg = f"[START] {component}"
    if details:
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        msg += f" | {details_str}"
    logger.info(msg)


def log_execution_end(logger: logging.Logger, component: str, status: str = "SUCCESS", duration: float = None):
    """Log the end of execution with status."""
    msg = f"[END] {component} - Status: {status}"
    if duration:
        msg += f" | Duration: {duration:.2f}s"
    logger.info(msg)


def log_error(logger: logging.Logger, component: str, error: Exception, context: dict = None):
    """Log error with context for debugging."""
    msg = f"[ERROR] {component} - {error.__class__.__name__}: {str(error)}"
    if context:
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        msg += f" | Context: {context_str}"
    logger.error(msg, exc_info=True)


def log_debug_data(logger: logging.Logger, component: str, data: dict):
    """Log debug data for analysis."""
    logger.debug(f"[DEBUG] {component} - Data: {data}")


# Default logger instance
logger = setup_logger()

