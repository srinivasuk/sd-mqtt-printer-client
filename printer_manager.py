"""
USB Printer Manager for SD MQTT Printer Mac client.
Handles USB thermal printer communication with ESC/POS commands.
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from escpos.printer import Usb, Dummy
from escpos.exceptions import USBNotFoundError, Error as ESCPOSError
import subprocess
import platform

from config import config
from utils.logger import logger
from utils.formatting import PrinterFormatter, parse_line_command, parse_qr_command, generate_line_pattern, replace_variables
from utils.bitmap import decode_bit_packed_bitmap, convert_bitmap_to_escpos
from qr_generator import qr_generator


class PrinterStatus:
    """Printer status constants compatible with ESP32 firmware."""
    READY = "ready"
    PAPER_OUT = "paper_out"
    PAPER_LOW = "paper_low"
    COVER_OPEN = "cover_open"
    CUTTER_ERROR = "cutter_error"
    OVERHEAT = "overheat"
    MECHANICAL_ERROR = "mechanical_error"
    OFFLINE = "offline"


class USBPrinterManager:
    """
    USB thermal printer manager with ESP32 firmware compatibility.
    Handles ESC/POS commands and printer status monitoring.
    """

    def __init__(self):
        self.printer = None
        self.is_connected = False
        self.formatter = PrinterFormatter()
        self.last_status_check = 0
        self.status_check_interval = 30  # seconds
        self.current_status = PrinterStatus.OFFLINE

        # Error state tracking
        self.error_states = {
            "paper_out": False,
            "paper_low": False,
            "cover_open": False,
            "cutter_error": False,
            "overheat": False,
            "mechanical_error": False,
        }

        # Print statistics
        self.print_stats = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "last_print_time": None,
        }

    def connect(self) -> bool:
        """
        Connect to USB thermal printer.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info(f"🔌 Connecting to USB printer: {config.PRINTER_NAME}")

            # Try to connect using printer name first
            if self._connect_by_name():
                return True

            # Try to connect using vendor/product ID
            if self._connect_by_ids():
                return True

            # Try to find any available thermal printer
            if self._connect_auto_detect():
                return True

            logger.error("❌ Failed to connect to any USB printer")
            return False

        except Exception as e:
            logger.error(f"❌ Printer connection error: {str(e)}")
            return False

    def _connect_by_name(self) -> bool:
        """Connect using printer name."""
        try:
            # Use lp command to print to named printer
            result = subprocess.run(['lpstat', '-p', config.PRINTER_NAME],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Printer exists, create a wrapper
                self.printer = NamedPrinterWrapper(config.PRINTER_NAME)
                self.is_connected = True
                self.current_status = PrinterStatus.READY
                logger.info(f"✅ Connected to printer: {config.PRINTER_NAME}")
                return True
        except Exception as e:
            logger.debug(f"🔍 Name-based connection failed: {str(e)}")

        return False

    def _connect_by_ids(self) -> bool:
        """Connect using vendor/product IDs."""
        try:
            vendor_id = int(config.PRINTER_VENDOR_ID, 16)
            product_id = int(config.PRINTER_PRODUCT_ID, 16)

            self.printer = Usb(vendor_id, product_id)
            self.is_connected = True
            self.current_status = PrinterStatus.READY
            logger.info(f"✅ Connected to USB printer: {vendor_id:04x}:{product_id:04x}")
            return True

        except (USBNotFoundError, ValueError) as e:
            logger.debug(f"🔍 ID-based connection failed: {str(e)}")

        return False

    def _connect_auto_detect(self) -> bool:
        """Auto-detect and connect to available thermal printer."""
        try:
            # List available printers
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'printer' in line and 'enabled' in line:
                        printer_name = line.split()[1]
                        if any(keyword in printer_name.lower() for keyword in ['thermal', 'receipt', 'pos', '80mm']):
                            try:
                                self.printer = NamedPrinterWrapper(printer_name)
                                self.is_connected = True
                                self.current_status = PrinterStatus.READY
                                logger.info(f"✅ Auto-detected printer: {printer_name}")
                                return True
                            except Exception:
                                continue
        except Exception as e:
            logger.debug(f"🔍 Auto-detection failed: {str(e)}")

        return False

    def disconnect(self):
        """Disconnect from printer."""
        if self.printer:
            try:
                if hasattr(self.printer, 'close'):
                    self.printer.close()
            except Exception as e:
                logger.debug(f"🔍 Disconnect error: {str(e)}")
            finally:
                self.printer = None
                self.is_connected = False
                self.current_status = PrinterStatus.OFFLINE
                logger.info("🔌 Printer disconnected")

    def reconnect(self) -> bool:
        """Reconnect to printer."""
        logger.info("🔄 Attempting printer reconnection...")
        self.disconnect()
        time.sleep(2)
        return self.connect()

    def print_receipt(self, receipt_data: List[Any]) -> bool:
        """
        Print receipt data compatible with ESP32 firmware format.

        Args:
            receipt_data: List of receipt elements (same format as ESP32)

        Returns:
            True if printed successfully, False otherwise
        """
        if not self.is_connected:
            logger.error("❌ Printer not connected")
            return False

        try:
            logger.debug(f"🖨️ Starting receipt print", elements=len(receipt_data))

            # Reset formatter state
            self.formatter.reset_formatting()

            # Initialize printer
            self.printer.init()

            # Process each element
            qr_printed = False
            for i, element in enumerate(receipt_data):
                try:
                    if isinstance(element, str):
                        # Text line
                        self._print_text_line(element)

                    elif isinstance(element, dict):
                        # Format or command object
                        if "f" in element:
                            # Format command
                            self._apply_format(element)

                        elif "line" in element:
                            # Line drawing command
                            self._print_line(element)

                        elif any(qr_key in element for qr_key in ["qr_bitmap", "qr_url", "qr"]):
                            # QR code command
                            if not qr_printed:  # Prevent duplicate QR codes
                                self._print_qr_code(element)
                                qr_printed = True

                        elif "m" in element and "order_id" in element["m"]:
                            # Metadata (usually page info)
                            logger.debug(f"📄 Receipt metadata", order_id=element["m"]["order_id"])

                        else:
                            logger.debug(f"🔍 Unknown element type: {element}")

                except Exception as e:
                    logger.error(f"❌ Error processing element {i}: {str(e)}")
                    continue

            # Final formatting and cut
            self._finalize_receipt()

            # Update statistics
            self.print_stats["total_jobs"] += 1
            self.print_stats["successful_jobs"] += 1
            self.print_stats["last_print_time"] = time.time()

            logger.info(f"✅ Receipt printed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Print error: {str(e)}")
            self.print_stats["total_jobs"] += 1
            self.print_stats["failed_jobs"] += 1
            return False

    def _print_text_line(self, text: str):
        """Print a text line with current formatting."""
        if not text:
            # Empty line
            self.printer.text("\n")
            return

        # Apply current formatting
        if self.formatter.current_align == 'C':
            self.printer.set_with_default(align='center')
        elif self.formatter.current_align == 'R':
            self.printer.set_with_default(align='right')
        else:
            self.printer.set_with_default(align='left')

        # Apply text styling
        if self.formatter.current_bold:
            self.printer.set_with_default(bold=True)
        else:
            self.printer.set_with_default(bold=False)

        # Apply size
        if self.formatter.current_size == 2:
            self.printer.set_with_default(double_height=True, double_width=True)
        elif self.formatter.current_size == 0:
            self.printer.set_with_default(double_height=False, double_width=False)
        else:
            self.printer.set_with_default(double_height=False, double_width=False)

        # Print text
        self.printer.text(text + "\n")

    def _apply_format(self, format_element: Dict[str, Any]):
        """Apply formatting changes."""
        changes = self.formatter.apply_format(format_element)
        logger.debug(f"🎨 Format applied", changes=changes)

    def _print_line(self, line_element: Dict[str, Any]):
        """Print a line element."""
        line_config = parse_line_command(line_element)

        # Generate line pattern
        line_pattern = generate_line_pattern(
            line_config["type"],
            line_config["width"],
            line_config["thickness"]
        )

        # Print line with center alignment
        self.printer.set_with_default(align='center')
        self.printer.text(line_pattern + "\n")

        logger.debug(f"📏 Line printed", type=line_config["type"], width=line_config["width"])

    def _print_qr_code(self, qr_element: Dict[str, Any]):
        """Print QR code element."""
        qr_data = parse_qr_command(qr_element)

        if not qr_data:
            logger.warning("⚠️ Invalid QR code data")
            return

        try:
            # Set alignment
            if qr_data["alignment"] == "center":
                self.printer.set_with_default(align='center')
            elif qr_data["alignment"] == "right":
                self.printer.set_with_default(align='right')
            else:
                self.printer.set_with_default(align='left')

            if qr_data["type"] == "bitmap":
                # Print bitmap QR code
                self._print_qr_bitmap(qr_data)
            else:
                # Print URL QR code using ESC/POS QR command
                self._print_qr_url(qr_data)

            logger.debug(f"🔲 QR code printed", type=qr_data["type"], size=qr_data["size"])

        except Exception as e:
            logger.error(f"❌ QR print error: {str(e)}")
            # Fallback: print QR URL as text
            self.printer.text("QR Code: " + qr_data.get("url", "N/A") + "\n")

    def _print_qr_bitmap(self, qr_data: Dict[str, Any]):
        """Print QR code from bitmap data."""
        try:
            width = qr_data["width"]
            height = qr_data["height"]
            bitmap_data = qr_data["data"]

            # Convert to ESC/POS format
            escpos_data = convert_bitmap_to_escpos(bitmap_data, width, height)

            # Send to printer
            self.printer._raw(escpos_data)

        except Exception as e:
            logger.error(f"❌ Bitmap QR print error: {str(e)}")
            raise

    def _print_qr_url(self, qr_data: Dict[str, Any]):
        """Print QR code from URL using ESC/POS QR command."""
        try:
            url = qr_data["url"]
            size = qr_data["size"]

            # Map size to ESC/POS QR size (1-16)
            escpos_size = max(1, min(16, size))

            # Use python-escpos QR function
            self.printer.qr(url, size=escpos_size, center=True)

        except Exception as e:
            logger.error(f"❌ URL QR print error: {str(e)}")
            # Fallback to text
            self.printer.text(f"QR: {url}\n")

    def _finalize_receipt(self):
        """Finalize receipt printing."""
        # Add some space
        self.printer.text("\n\n")

        # Cut paper if supported
        try:
            self.printer.cut()
        except Exception:
            # If cut fails, just add more space
            self.printer.text("\n\n\n")

    def get_status(self) -> Dict[str, Any]:
        """
        Get printer status compatible with ESP32 firmware format.

        Returns:
            Status dictionary
        """
        current_time = time.time()

        # Only check status periodically to avoid overhead
        if current_time - self.last_status_check > self.status_check_interval:
            self._update_status()
            self.last_status_check = current_time

        return {
            "printer_online": self.is_connected,
            "printer_status": self.current_status,
            "paper_present": not self.error_states["paper_out"],
            "paper_near_end": self.error_states["paper_low"],
            "cover_closed": not self.error_states["cover_open"],
            "cutter_ok": not self.error_states["cutter_error"],
            "overheat": self.error_states["overheat"],
            "mechanical_error": self.error_states["mechanical_error"],
            "last_status_check": current_time,
            "print_stats": self.print_stats.copy()
        }

    def _update_status(self):
        """Update printer status by checking hardware."""
        if not self.is_connected:
            self.current_status = PrinterStatus.OFFLINE
            return

        try:
            # For USB printers, we have limited status checking
            # Most USB thermal printers don't provide detailed status

            # Try to send a simple command to test connection
            if hasattr(self.printer, '_raw'):
                # Send status request command (if supported)
                try:
                    self.printer._raw(b'\x10\x04\x01')  # DLE EOT n (status request)
                    # If no exception, printer is responsive
                    self.current_status = PrinterStatus.READY
                except Exception:
                    # If command fails, assume printer issues
                    self.current_status = PrinterStatus.OFFLINE
            else:
                # For named printers, check if printer queue is available
                result = subprocess.run(['lpstat', '-p', config.PRINTER_NAME],
                                      capture_output=True, text=True)
                if result.returncode == 0 and 'enabled' in result.stdout:
                    self.current_status = PrinterStatus.READY
                else:
                    self.current_status = PrinterStatus.OFFLINE

        except Exception as e:
            logger.debug(f"🔍 Status check error: {str(e)}")
            self.current_status = PrinterStatus.OFFLINE

    def test_print(self) -> bool:
        """
        Print a test receipt.

        Returns:
            True if test printed successfully
        """
        test_receipt = [
            {"f": {"a": "c", "b": True, "s": 2}},
            "SD MQTT Printer Test",
            {"f": {"a": "l", "b": False, "s": 1}},
            "",
            "Test Date: " + time.strftime("%Y-%m-%d %H:%M:%S"),
            "Printer: " + config.PRINTER_NAME,
            "Status: Connected",
            "",
            {"line": "solid"},
            "",
            {"f": {"a": "c"}},
            "QR Code Test:",
            "",
            qr_generator.create_test_qr(),
            "",
            {"f": {"a": "c", "b": True}},
            "Test Completed Successfully!",
            {"f": {"a": "l", "b": False}},
            ""
        ]

        return self.print_receipt(test_receipt)


class NamedPrinterWrapper:
    """Wrapper for system printers accessed by name via lp command."""

    def __init__(self, printer_name: str):
        self.printer_name = printer_name

    def init(self):
        """Initialize printer (no-op for lp)."""
        pass

    def text(self, text: str):
        """Add text to print buffer."""
        if not hasattr(self, '_buffer'):
            self._buffer = b""
        self._buffer += text.encode('utf-8')

    def set_with_default(self, **kwargs):
        """Set formatting (simplified for lp)."""
        # For lp printers, we have limited formatting control
        pass

    def qr(self, text: str, size: int = 6, center: bool = True):
        """Print QR code (fallback to text for lp)."""
        if center:
            self.text(f"\n    QR: {text}\n\n")
        else:
            self.text(f"QR: {text}\n")

    def cut(self):
        """Cut paper (add extra spacing for lp)."""
        self.text("\n\n\n")

    def _raw(self, data: bytes):
        """Send raw data to printer."""
        if not hasattr(self, '_buffer'):
            self._buffer = b""
        self._buffer += data

    def close(self):
        """Send buffered data to printer and close."""
        if hasattr(self, '_buffer') and self._buffer:
            try:
                # Send to printer via lp command
                process = subprocess.Popen(['lp', '-d', self.printer_name],
                                         stdin=subprocess.PIPE)
                process.communicate(input=self._buffer)
                self._buffer = b""
            except Exception as e:
                logger.error(f"❌ lp print error: {str(e)}")


# Global printer manager instance
printer_manager = USBPrinterManager()
