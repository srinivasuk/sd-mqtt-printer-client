#!/usr/bin/env python3
"""
SD MQTT Printer Mac - Main Application
A Python port of ESP32 thermal printer firmware for Mac systems with USB printers.

This application maintains 100% compatibility with the existing MQTT server infrastructure
while adapting to USB printer hardware on macOS.
"""

import sys
import time
import signal
import threading
from typing import Optional

from config import config
from utils.logger import logger
from printer_manager import printer_manager
from mqtt_client import mqtt_client
from qr_generator import qr_generator


class PrinterClientApp:
    """Main application class for the SD MQTT Printer Mac client."""

    def __init__(self):
        self.running = False
        self.startup_time = time.time()
        self.status_thread = None
        self.recovery_attempts = 0
        self.max_recovery_attempts = 5

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self) -> bool:
        """
        Start the printer client application.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("🚀 Starting SD MQTT Printer Mac client...")
            logger.info(str(config))

            # Log system information
            self._log_system_info()

            # Connect to printer
            if not self._connect_printer():
                return False

            # Connect to MQTT broker
            if not self._connect_mqtt():
                return False

            # Start status monitoring
            self._start_status_monitoring()

            # Mark as running
            self.running = True

            logger.info("✅ SD MQTT Printer Mac client started successfully")
            logger.info(f"📡 Listening for print commands on: {config.TOPIC_PRINT}")
            logger.info(f"💓 Sending heartbeats to: {config.TOPIC_HEARTBEAT}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start application: {str(e)}")
            return False

    def stop(self):
        """Stop the printer client application."""
        logger.info("🛑 Stopping SD MQTT Printer Mac client...")

        self.running = False

        # Stop status monitoring
        if self.status_thread:
            self.status_thread.join(timeout=5)

        # Disconnect MQTT
        mqtt_client.disconnect()

        # Disconnect printer
        printer_manager.disconnect()

        logger.info("✅ SD MQTT Printer Mac client stopped")

    def run(self):
        """Run the main application loop."""
        if not self.start():
            logger.error("❌ Failed to start application")
            return False

        try:
            # Main loop
            while self.running:
                # Check connections and recover if needed
                self._check_and_recover()

                # Sleep for a short time
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("📝 Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Application error: {str(e)}")
        finally:
            self.stop()

        return True

    def _connect_printer(self) -> bool:
        """Connect to the USB printer."""
        logger.info("🖨️ Connecting to USB printer...")

        if printer_manager.connect():
            logger.info("✅ Printer connected successfully")

            # Run a test print if in debug mode
            if config.DEBUG_MODE:
                logger.info("🧪 Running printer test...")
                if printer_manager.test_print():
                    logger.info("✅ Printer test successful")
                else:
                    logger.warning("⚠️ Printer test failed")

            return True
        else:
            logger.error("❌ Failed to connect to printer")
            return False

    def _connect_mqtt(self) -> bool:
        """Connect to the MQTT broker."""
        logger.info("📡 Connecting to MQTT broker...")

        if mqtt_client.connect():
            logger.info("✅ MQTT connected successfully")
            return True
        else:
            logger.error("❌ Failed to connect to MQTT broker")
            return False

    def _start_status_monitoring(self):
        """Start status monitoring thread."""
        self.status_thread = threading.Thread(target=self._status_monitoring_loop, daemon=True)
        self.status_thread.start()
        logger.info("📊 Status monitoring started")

    def _status_monitoring_loop(self):
        """Status monitoring loop."""
        while self.running:
            try:
                # Log periodic status
                if config.DEBUG_MODE:
                    self._log_status()

                # Sleep for status check interval
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ Status monitoring error: {str(e)}")
                time.sleep(10)

    def _check_and_recover(self):
        """Check connections and attempt recovery if needed."""
        try:
            # Check printer connection
            if not printer_manager.is_connected:
                logger.warning("⚠️ Printer disconnected, attempting recovery...")
                if printer_manager.reconnect():
                    logger.info("✅ Printer reconnected")
                    self.recovery_attempts = 0
                else:
                    self.recovery_attempts += 1
                    logger.error(f"❌ Printer recovery failed (attempt {self.recovery_attempts})")

            # Check MQTT connection
            if not mqtt_client.is_connected:
                logger.warning("⚠️ MQTT disconnected, attempting recovery...")
                if mqtt_client.reconnect():
                    logger.info("✅ MQTT reconnected")
                    mqtt_client.send_recovery_message()
                    self.recovery_attempts = 0
                else:
                    self.recovery_attempts += 1
                    logger.error(f"❌ MQTT recovery failed (attempt {self.recovery_attempts})")

            # Check if too many recovery attempts
            if self.recovery_attempts >= self.max_recovery_attempts:
                logger.critical("🚨 Too many recovery attempts, stopping application")
                self.running = False

        except Exception as e:
            logger.error(f"❌ Recovery check error: {str(e)}")

    def _log_system_info(self):
        """Log system information."""
        try:
            import platform
            import psutil

            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
            }

            logger.system_info(system_info)

        except Exception as e:
            logger.debug(f"🔍 System info error: {str(e)}")

    def _log_status(self):
        """Log current status."""
        try:
            uptime = int(time.time() - self.startup_time)
            printer_status = printer_manager.get_status()
            mqtt_info = mqtt_client.get_connection_info()

            status_info = {
                "uptime_seconds": uptime,
                "printer_connected": printer_status["printer_online"],
                "printer_status": printer_status["printer_status"],
                "mqtt_connected": mqtt_info["connected"],
                "messages_received": mqtt_info["stats"]["messages_received"],
                "print_jobs_completed": printer_status["print_stats"]["successful_jobs"],
                "recovery_attempts": self.recovery_attempts,
            }

            logger.info("📊 Status update", **status_info)

        except Exception as e:
            logger.debug(f"🔍 Status log error: {str(e)}")

    def _signal_handler(self, signum, frame):
        """Handle system signals."""
        logger.info(f"📝 Received signal {signum}")
        self.running = False

    def get_status(self) -> dict:
        """Get comprehensive application status."""
        return {
            "running": self.running,
            "uptime": int(time.time() - self.startup_time),
            "printer": printer_manager.get_status(),
            "mqtt": mqtt_client.get_connection_info(),
            "recovery_attempts": self.recovery_attempts,
            "config": {
                "printer_name": config.PRINTER_NAME,
                "printer_id": config.PRINTER_ID,
                "mqtt_broker": config.MQTT_BROKER,
                "heartbeat_interval": config.HEARTBEAT_INTERVAL,
                "debug_mode": config.DEBUG_MODE,
            }
        }


def main():
    """Main entry point."""
    try:
        # Create and run application
        app = PrinterClientApp()

        # Print startup banner
        print("=" * 60)
        print("🖨️  SD MQTT Printer Mac Client")
        print("=" * 60)
        print(f"📱 Printer ID: {config.PRINTER_ID}")
        print(f"🖨️  Printer: {config.PRINTER_NAME}")
        print(f"📡 MQTT Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}")
        print(f"🔑 MQTT Username: {config.MQTT_USERNAME}")
        print(f"💓 Heartbeat: {config.HEARTBEAT_INTERVAL}s")
        print("=" * 60)

        # Run the application
        success = app.run()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.critical(f"🚨 Critical error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
