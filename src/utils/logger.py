"""
Logging utilities for SD MQTT Printer Mac client.
Provides structured logging with file rotation and console output.
"""

import logging
import logging.handlers
import sys
from datetime import datetime
from typing import Optional

from ..config import config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


class PrinterLogger:
    """Printer-specific logger with enhanced formatting."""

    def __init__(self, name: str = "printer_client"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup file and console handlers."""

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=self._parse_size(config.LOG_MAX_SIZE),
            backupCount=config.LOG_BACKUP_COUNT
        )

        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes."""
        size_str = size_str.upper()

        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message, **kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message(message, **kwargs))

    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with additional context."""
        if kwargs:
            context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} | {context}"
        return message

    # Printer-specific logging methods
    def print_start(self, order_id: str, page: int, total_pages: int):
        """Log print job start."""
        self.info(f"🖨️ Print started",
                 order_id=order_id,
                 page=page,
                 total_pages=total_pages)

    def print_complete(self, order_id: str, page: int, total_pages: int):
        """Log print job completion."""
        self.info(f"✅ Print completed",
                 order_id=order_id,
                 page=page,
                 total_pages=total_pages)

    def print_error(self, order_id: str, error: str):
        """Log print error."""
        self.error(f"❌ Print error",
                  order_id=order_id,
                  error=error)

    def mqtt_connect(self, broker: str, port: int):
        """Log MQTT connection."""
        self.info(f"🔌 MQTT connected",
                 broker=broker,
                 port=port)

    def mqtt_disconnect(self, reason: str = ""):
        """Log MQTT disconnection."""
        self.warning(f"🔌 MQTT disconnected",
                    reason=reason)

    def mqtt_message(self, topic: str, size: int):
        """Log MQTT message received."""
        self.debug(f"📨 MQTT message",
                  topic=topic,
                  size=size)

    def heartbeat_sent(self, status: str):
        """Log heartbeat sent."""
        self.debug(f"💓 Heartbeat sent",
                  status=status)

    def qr_generated(self, url: str, size: int):
        """Log QR code generation."""
        self.debug(f"🔲 QR generated",
                  url=url[:50] + "..." if len(url) > 50 else url,
                  size=size)

    def printer_status(self, status: str, details: Optional[dict] = None):
        """Log printer status."""
        if details:
            self.debug(f"🖨️ Printer status: {status}", **details)
        else:
            self.debug(f"🖨️ Printer status: {status}")

    def system_info(self, info: dict):
        """Log system information."""
        self.info(f"💻 System info", **info)


# Global logger instance
logger = PrinterLogger()
