"""
MQTT Client for SD MQTT Printer Mac client.
Handles MQTT communication with the server using the same protocol as ESP32 firmware.
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Callable
import paho.mqtt.client as mqtt
from datetime import datetime

from .config import config
from .utils.logger import logger
from .printer_manager import printer_manager
from .utils.formatting import replace_variables


class MQTTClient:
    """
    MQTT client with ESP32 firmware compatibility.
    Handles heartbeat, print commands, and status reporting.
    """

    def __init__(self):
        self.client = None
        self.is_connected = False
        self.last_heartbeat = 0
        self.heartbeat_thread = None
        self.running = False

        # Message handlers
        self.message_handlers = {
            config.TOPIC_PRINT: self._handle_print_message,
        }

        # Statistics
        self.stats = {
            "connection_time": None,
            "messages_received": 0,
            "messages_sent": 0,
            "print_jobs_received": 0,
            "print_jobs_completed": 0,
            "last_message_time": None,
            "reconnect_count": 0,
        }

    def connect(self) -> bool:
        """
        Connect to MQTT broker.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info(f"🔌 Connecting to MQTT broker: {config.MQTT_BROKER}:{config.MQTT_PORT}")

            # Create MQTT client
            self.client = mqtt.Client(client_id=config.CLIENT_ID)

            # Set credentials
            self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            # Connect to broker
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)

            # Start network loop
            self.client.loop_start()

            # Wait for connection
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < 10:
                time.sleep(0.1)

            if self.is_connected:
                logger.mqtt_connect(config.MQTT_BROKER, config.MQTT_PORT)
                self.stats["connection_time"] = time.time()
                self._start_heartbeat()
                return True
            else:
                logger.error("❌ MQTT connection timeout")
                return False

        except Exception as e:
            logger.error(f"❌ MQTT connection error: {str(e)}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.running = False

        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)

        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                logger.debug(f"🔍 MQTT disconnect error: {str(e)}")

        self.is_connected = False
        logger.mqtt_disconnect()

    def reconnect(self) -> bool:
        """Reconnect to MQTT broker."""
        logger.info("🔄 Attempting MQTT reconnection...")
        self.disconnect()
        time.sleep(2)
        success = self.connect()
        if success:
            self.stats["reconnect_count"] += 1
        return success

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection callback."""
        if rc == 0:
            self.is_connected = True
            logger.info(f"✅ MQTT connected with result code {rc}")

            # Subscribe to print topic with QoS 0 to avoid issues
            client.subscribe(config.TOPIC_PRINT, qos=0)
            logger.info(f"📡 Subscribed to print topic: {config.TOPIC_PRINT}")

            # Skip initial status to test if it's causing disconnections
            # self._send_status()

        else:
            logger.error(f"❌ MQTT connection failed with result code {rc}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection callback."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"⚠️ MQTT unexpected disconnection (code: {rc})")
            # Common disconnect reason codes
            if rc == 1:
                logger.warning("   Reason: Incorrect protocol version")
            elif rc == 2:
                logger.warning("   Reason: Invalid client identifier")
            elif rc == 3:
                logger.warning("   Reason: Server unavailable")
            elif rc == 4:
                logger.warning("   Reason: Bad username or password")
            elif rc == 5:
                logger.warning("   Reason: Not authorized")
            elif rc == 7:
                logger.warning("   Reason: Connection lost")
            else:
                logger.warning(f"   Reason: Unknown error code {rc}")
        else:
            logger.info("🔌 MQTT disconnected gracefully")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            logger.mqtt_message(topic, len(payload))

            # Update statistics
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = time.time()

            # Handle message based on topic
            if topic in self.message_handlers:
                self.message_handlers[topic](payload)
            else:
                logger.warning(f"⚠️ Unknown topic: {topic}")

        except Exception as e:
            logger.error(f"❌ Message handling error: {str(e)}")

    def _on_publish(self, client, userdata, mid):
        """Handle MQTT publish callback."""
        self.stats["messages_sent"] += 1
        logger.debug(f"📤 Message published: {mid}")

    def _handle_print_message(self, payload: str):
        """
        Handle print command messages.

        Args:
            payload: JSON string with print data
        """
        try:
            logger.info(f"📨 Print message received")

            # Parse JSON payload
            print_data = json.loads(payload)

            # Update statistics
            self.stats["print_jobs_received"] += 1

            # Extract print information
            order_id = print_data.get("order_id", "unknown")
            page = print_data.get("page", 1)
            total_pages = print_data.get("total_pages", 1)
            receipt_data = print_data.get("receipt_data", [])

            logger.print_start(order_id, page, total_pages)

            # Process receipt data with variable replacement
            processed_receipt = self._process_receipt_data(receipt_data, print_data)

            # Send to printer
            if printer_manager.print_receipt(processed_receipt):
                logger.print_complete(order_id, page, total_pages)
                self.stats["print_jobs_completed"] += 1

                # Send success status
                self._send_print_status(order_id, page, "completed")
            else:
                logger.print_error(order_id, "Print failed")
                self._send_print_status(order_id, page, "failed")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in print message: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Print message handling error: {str(e)}")

    def _process_receipt_data(self, receipt_data: list, print_data: dict) -> list:
        """
        Process receipt data with variable replacement.

        Args:
            receipt_data: Raw receipt data from server
            print_data: Full print data for variable replacement

        Returns:
            Processed receipt data
        """
        processed_data = []

        for element in receipt_data:
            if isinstance(element, str):
                # Replace variables in text
                processed_text = replace_variables(element, print_data)
                processed_data.append(processed_text)
            elif isinstance(element, dict):
                # Process dictionary elements
                processed_element = {}
                for key, value in element.items():
                    if isinstance(value, str):
                        processed_element[key] = replace_variables(value, print_data)
                    else:
                        processed_element[key] = value
                processed_data.append(processed_element)
            else:
                # Pass through other types
                processed_data.append(element)

        return processed_data

    def _send_heartbeat(self):
        """Send heartbeat message to server."""
        try:
            # Get printer status to match ESP32 firmware format
            printer_status = printer_manager.get_status()
            
            # Get system network information
            local_ip = self._get_local_ip()
            wifi_rssi = self._get_wifi_signal_strength()
            
            # Create comprehensive heartbeat message matching ESP32 firmware format EXACTLY
            heartbeat_data = {
                "printer_id": config.PRINTER_ID,
                "timestamp": int(time.time() * 1000),  # Milliseconds like ESP32
                "esp32_status": "online",  # Mac client is online if sending this
                "printer_online": printer_status["printer_online"],
                "printer_status": printer_status["printer_status"],
                "details": {
                    "paper_present": printer_status.get("paper_present", True),
                    "cover_closed": printer_status.get("cover_closed", True),
                    "cutter_ok": printer_status.get("cutter_ok", True),
                    "wifi_connected": True,  # Mac client uses WiFi/Ethernet
                    "mqtt_connected": self.is_connected,
                    "free_heap": self._get_system_memory(),
                    "uptime_ms": int(time.time() * 1000),
                    "wifi_rssi": wifi_rssi,
                    "local_ip": local_ip
                }
            }

            # Send heartbeat
            self._publish(config.TOPIC_HEARTBEAT, heartbeat_data)

            logger.info(f"💓 Heartbeat sent to {config.TOPIC_HEARTBEAT}")

        except Exception as e:
            logger.error(f"❌ Heartbeat error: {str(e)}")

    def _send_status(self):
        """Send status update to server."""
        try:
            printer_status = printer_manager.get_status()

            status_data = {
                "timestamp": int(time.time() * 1000),
                "printer_id": config.PRINTER_ID,
                "status": printer_status["printer_status"],
                "online": printer_status["printer_online"],
                "details": printer_status
            }

            self._publish(config.TOPIC_STATUS, status_data)

        except Exception as e:
            logger.error(f"❌ Status send error: {str(e)}")

    def _send_print_status(self, order_id: str, page: int, status: str):
        """
        Send print job status to server.

        Args:
            order_id: Order ID
            page: Page number
            status: Print status (completed, failed, etc.)
        """
        try:
            status_data = {
                "timestamp": int(time.time() * 1000),
                "printer_id": config.PRINTER_ID,
                "order_id": order_id,
                "page": page,
                "status": status,
                "print_time": time.time()
            }

            # Send to status topic
            self._publish(config.TOPIC_STATUS, status_data)

        except Exception as e:
            logger.error(f"❌ Print status send error: {str(e)}")

    def _send_error(self, error_type: str, error_message: str):
        """
        Send error message to server.

        Args:
            error_type: Type of error
            error_message: Error description
        """
        try:
            error_data = {
                "timestamp": int(time.time() * 1000),
                "printer_id": config.PRINTER_ID,
                "error_type": error_type,
                "error_message": error_message,
                "printer_status": printer_manager.get_status()
            }

            self._publish(config.TOPIC_ERROR, error_data)

        except Exception as e:
            logger.error(f"❌ Error send error: {str(e)}")

    def _publish(self, topic: str, data: dict):
        """
        Publish data to MQTT topic.

        Args:
            topic: MQTT topic
            data: Data to publish
        """
        if not self.is_connected:
            logger.warning("⚠️ Cannot publish - MQTT not connected")
            return

        try:
            payload = json.dumps(data)
            result = self.client.publish(topic, payload, qos=0)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"📤 Published to {topic}", size=len(payload))
            else:
                logger.error(f"❌ Publish failed: {result.rc}")

        except Exception as e:
            logger.error(f"❌ Publish error: {str(e)}")

    def _start_heartbeat(self):
        """Start heartbeat thread."""
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info(f"💓 Heartbeat started (interval: {config.HEARTBEAT_INTERVAL}s)")

    def _heartbeat_loop(self):
        """Heartbeat loop thread."""
        # Send first heartbeat immediately
        self._send_heartbeat()
        self.last_heartbeat = time.time()
        
        while self.running and self.is_connected:
            try:
                current_time = time.time()

                # Send heartbeat if interval has passed
                if current_time - self.last_heartbeat >= config.HEARTBEAT_INTERVAL:
                    self._send_heartbeat()
                    self.last_heartbeat = current_time

                # Sleep for 1 second
                time.sleep(1)

            except Exception as e:
                logger.error(f"❌ Heartbeat loop error: {str(e)}")
                time.sleep(5)

    def _get_system_memory(self) -> int:
        """Get system memory usage (simplified for Mac)."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return int(memory.available / 1024 / 1024)  # MB
        except Exception:
            return 0

    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            import socket
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _get_wifi_signal_strength(self) -> int:
        """Get WiFi signal strength (Mac specific)."""
        try:
            import subprocess
            result = subprocess.run([
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                "-I"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'agrCtlRSSI' in line:
                        rssi = int(line.split(':')[1].strip())
                        return rssi
        except Exception:
            pass
        return -50  # Default reasonable value

    def get_connection_info(self) -> dict:
        """Get connection information."""
        return {
            "connected": self.is_connected,
            "broker": config.MQTT_BROKER,
            "port": config.MQTT_PORT,
            "client_id": config.CLIENT_ID,
            "topics": config.get_topics(),
            "stats": self.stats.copy()
        }

    def send_recovery_message(self):
        """Send recovery message after reconnection."""
        try:
            recovery_data = {
                "timestamp": int(time.time() * 1000),
                "printer_id": config.PRINTER_ID,
                "message": "Printer client recovered and reconnected",
                "uptime": int(time.time() - self.stats["connection_time"]) if self.stats["connection_time"] else 0,
                "reconnect_count": self.stats["reconnect_count"]
            }

            self._publish(config.TOPIC_RECOVERY, recovery_data)

        except Exception as e:
            logger.error(f"❌ Recovery message error: {str(e)}")


# Global MQTT client instance
mqtt_client = MQTTClient()
