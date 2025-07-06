"""
Configuration management for SD MQTT Printer Mac client.
Handles loading and validation of environment variables and settings.
"""

import os
import uuid
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the printer client."""

    def __init__(self):
        self._load_config()
        self._validate_config()

    def _load_config(self):
        """Load configuration from environment variables."""

        # MQTT Configuration
        self.MQTT_BROKER = os.getenv("MQTT_BROKER", "printer.scandeer.com")
        self.MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
        self.MQTT_USERNAME = os.getenv("MQTT_USERNAME", "vimal1")
        self.MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "pa55word")
        self.MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
        self.MQTT_QOS = int(os.getenv("MQTT_QOS", "1"))

        # Printer Configuration
        self.PRINTER_NAME = os.getenv("PRINTER_NAME", "gobbler_80mm_Series")
        self.PRINTER_VENDOR_ID = os.getenv("PRINTER_VENDOR_ID", "0x04b8")
        self.PRINTER_PRODUCT_ID = os.getenv("PRINTER_PRODUCT_ID", "0x0202")

        # System Configuration
        mac_address = os.getenv("MAC_ADDRESS", "auto")
        if mac_address == "auto":
            # Generate MAC address from system UUID
            self.MAC_ADDRESS = self._generate_mac_address()
        else:
            self.MAC_ADDRESS = mac_address

        self.HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
        self.DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

        # QR Code Configuration
        self.QR_ERROR_CORRECTION = os.getenv("QR_ERROR_CORRECTION", "M")
        self.QR_BORDER = int(os.getenv("QR_BORDER", "4"))
        self.QR_BOX_SIZE = int(os.getenv("QR_BOX_SIZE", "10"))

        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "printer_client.log")
        self.LOG_MAX_SIZE = os.getenv("LOG_MAX_SIZE", "10MB")
        self.LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

        # Derived configurations
        self.PRINTER_ID = self.MAC_ADDRESS.replace(":", "")
        self.CLIENT_ID = f"PrinterClient-{self.PRINTER_ID}"

        # MQTT Topics (same format as ESP32 firmware)
        self.TOPIC_PRINT = f"{self.MQTT_USERNAME}/pt/{self.PRINTER_ID}/p"
        self.TOPIC_STATUS = f"{self.MQTT_USERNAME}/pt/{self.PRINTER_ID}/a"
        self.TOPIC_HEARTBEAT = f"{self.MQTT_USERNAME}/pt/{self.PRINTER_ID}/h"
        self.TOPIC_ERROR = f"{self.MQTT_USERNAME}/pt/{self.PRINTER_ID}/e"
        self.TOPIC_RECOVERY = f"{self.MQTT_USERNAME}/pt/{self.PRINTER_ID}/r"

    def _generate_mac_address(self) -> str:
        """Generate a consistent MAC address based on system UUID."""
        try:
            # Get system UUID
            system_uuid = str(uuid.getnode())

            # Convert to MAC address format
            mac_hex = hex(int(system_uuid))[2:].zfill(12)
            mac_address = ":".join([mac_hex[i:i+2] for i in range(0, 12, 2)])

            return mac_address.upper()
        except Exception:
            # Fallback to random MAC if system UUID fails
            return ":".join([f"{uuid.getnode():02x}" for _ in range(6)])

    def _validate_config(self):
        """Validate configuration values."""

        # Validate MQTT configuration
        if not self.MQTT_BROKER:
            raise ValueError("MQTT_BROKER is required")

        if not (1 <= self.MQTT_PORT <= 65535):
            raise ValueError("MQTT_PORT must be between 1 and 65535")

        if not self.MQTT_USERNAME:
            raise ValueError("MQTT_USERNAME is required")

        if not self.MQTT_PASSWORD:
            raise ValueError("MQTT_PASSWORD is required")

        # Validate printer configuration
        if not self.PRINTER_NAME:
            raise ValueError("PRINTER_NAME is required")

        # Validate system configuration
        if not (1 <= self.HEARTBEAT_INTERVAL <= 300):
            raise ValueError("HEARTBEAT_INTERVAL must be between 1 and 300 seconds")

        # Validate QR configuration
        if self.QR_ERROR_CORRECTION not in ["L", "M", "Q", "H"]:
            raise ValueError("QR_ERROR_CORRECTION must be L, M, Q, or H")

        if not (0 <= self.QR_BORDER <= 20):
            raise ValueError("QR_BORDER must be between 0 and 20")

        if not (1 <= self.QR_BOX_SIZE <= 20):
            raise ValueError("QR_BOX_SIZE must be between 1 and 20")

    def get_printer_config(self) -> dict:
        """Get printer configuration as a dictionary."""
        return {
            "name": self.PRINTER_NAME,
            "vendor_id": self.PRINTER_VENDOR_ID,
            "product_id": self.PRINTER_PRODUCT_ID,
        }

    def get_mqtt_config(self) -> dict:
        """Get MQTT configuration as a dictionary."""
        return {
            "broker": self.MQTT_BROKER,
            "port": self.MQTT_PORT,
            "username": self.MQTT_USERNAME,
            "password": self.MQTT_PASSWORD,
            "keepalive": self.MQTT_KEEPALIVE,
            "qos": self.MQTT_QOS,
            "client_id": self.CLIENT_ID,
        }

    def get_topics(self) -> dict:
        """Get MQTT topics as a dictionary."""
        return {
            "print": self.TOPIC_PRINT,
            "status": self.TOPIC_STATUS,
            "heartbeat": self.TOPIC_HEARTBEAT,
            "error": self.TOPIC_ERROR,
            "recovery": self.TOPIC_RECOVERY,
        }

    def get_qr_config(self) -> dict:
        """Get QR code configuration as a dictionary."""
        return {
            "error_correction": self.QR_ERROR_CORRECTION,
            "border": self.QR_BORDER,
            "box_size": self.QR_BOX_SIZE,
        }

    def __str__(self) -> str:
        """String representation of configuration."""
        return f"""
SD MQTT Printer Mac Configuration:
==================================
MQTT Broker: {self.MQTT_BROKER}:{self.MQTT_PORT}
MQTT Username: {self.MQTT_USERNAME}
Printer: {self.PRINTER_NAME}
Printer ID: {self.PRINTER_ID}
MAC Address: {self.MAC_ADDRESS}
Client ID: {self.CLIENT_ID}
Heartbeat Interval: {self.HEARTBEAT_INTERVAL}s
Debug Mode: {self.DEBUG_MODE}

Topics:
- Print: {self.TOPIC_PRINT}
- Status: {self.TOPIC_STATUS}
- Heartbeat: {self.TOPIC_HEARTBEAT}
- Error: {self.TOPIC_ERROR}
- Recovery: {self.TOPIC_RECOVERY}
"""


# Global configuration instance
config = Config()
