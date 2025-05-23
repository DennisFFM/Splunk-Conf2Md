# bin/logger.py
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logger(
    name: str = "splunk-conf2md",
    log_file: Optional[Path] = None,
    console_level: str = "INFO",
    file_level: str = "DEBUG"
) -> logging.Logger:
    """
    Set up logger with console and file handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        console_level: Console logging level
        file_level: File logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, file_level.upper()))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name or "splunk-conf2md")