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

from .config import config
from .utils.logger import logger
from .utils.formatting import PrinterFormatter, parse_line_command, parse_qr_command, generate_line_pattern, replace_variables
from .utils.bitmap import decode_bit_packed_bitmap, convert_bitmap_to_escpos
from .qr_generator import qr_generator


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

    def print_receipt(self, receipt_data: list) -> bool:
        """
        Print receipt data with formatting support.
        Processes JSON elements exactly like ESP32 firmware.
        """
        try:
            logger.debug(f"🖨️ Starting receipt print", elements=len(receipt_data))

            # Initialize formatting state for new print job (like ESP32 firmware)
            self.formatter.reset_formatting()
            
            # Apply initial formatting to printer (like ESP32 firmware initialization)
            self._apply_current_format()
            logger.debug("🎨 Format state initialized for new print job")

            # Process each element exactly like ESP32 firmware
            qr_already_printed = False
            last_order_id = ""
            current_page = 1
            total_pages = 1
            
            for i, element in enumerate(receipt_data):
                logger.debug(f"🔍 Processing element {i}: {type(element)}")
                
                # Handle JSON objects (formatting and metadata)
                if isinstance(element, dict):
                    # Check for page metadata (like ESP32 firmware)
                    if "page" in element and "of" in element:
                        current_page = element.get("page", 1)
                        total_pages = element.get("of", 1)
                        logger.debug(f"📄 Page metadata: {current_page}/{total_pages}")
                        continue  # Skip printing this meta line
                    
                    # Apply formatting if present (like ESP32 applyShortFormat)
                    if "f" in element:
                        self._apply_short_format(element)
                        continue  # Skip to next element after applying format
                    
                    # Extract order ID from metadata
                    if "m" in element and "order_id" in element["m"]:
                        last_order_id = element["m"]["order_id"]
                        logger.debug(f"📋 Order ID extracted: {last_order_id}")
                        continue  # Skip to next element after extracting metadata
                    
                    # Handle line elements (MISSING LOGIC - this is why lines weren't printing!)
                    if "line" in element:
                        logger.debug(f"📏 Line element detected: {element}")
                        self._print_line(element)
                        continue  # Skip to next element after printing line
                    
                    # Handle QR codes (like ESP32 firmware QR processing)
                    if not qr_already_printed:
                        if "qr_bitmap" in element:
                            logger.debug("🔲 QR bitmap detected - converting to built-in QR")
                            qr_url = f"https://scandeer.com/order/{last_order_id}"
                            qr_size = element.get("qr_size", 10)
                            qr_align = element.get("qr_alignment", "center")
                            qr_data = {
                                "url": qr_url,
                                "size": qr_size,
                                "alignment": qr_align,
                                "type": "url"
                            }
                            self._print_qr_code(qr_data)
                            qr_already_printed = True
                            continue
                        elif "qr_image_url" in element:
                            logger.debug("🖼️ QR image URL detected")
                            qr_url = element["qr_image_url"]
                            qr_size = element.get("qr_size", 10)
                            qr_align = element.get("qr_alignment", "center")
                            qr_data = {
                                "url": qr_url,
                                "size": qr_size,
                                "alignment": qr_align,
                                "type": "url"
                            }
                            self._print_qr_code(qr_data)
                            qr_already_printed = True
                            continue
                        elif "qr_url" in element:
                            logger.debug("🌐 QR URL detected")
                            qr_data = {
                                "url": element["qr_url"],
                                "size": element.get("qr_size", 10),
                                "alignment": element.get("qr_alignment", "center"),
                                "type": "url"
                            }
                            self._print_qr_code(qr_data)
                            qr_already_printed = True
                            continue
                        elif "qr" in element:
                            logger.debug("🔲 Legacy QR detected")
                            if isinstance(element["qr"], str):
                                qr_data = {
                                    "text": element["qr"],
                                    "url": element["qr"],
                                    "size": 10,
                                    "alignment": "center",
                                    "type": "url"
                                }
                                self._print_qr_code(qr_data)
                            elif isinstance(element["qr"], dict):
                                qr_obj = element["qr"]
                                # Set defaults for missing fields
                                qr_data = {
                                    "text": qr_obj.get("text", qr_obj.get("url", "")),
                                    "url": qr_obj.get("url", qr_obj.get("text", "")),
                                    "size": qr_obj.get("size", 10),
                                    "alignment": qr_obj.get("alignment", "center"),
                                    "type": qr_obj.get("type", "url")
                                }
                                self._print_qr_code(qr_data)
                            qr_already_printed = True
                            continue
                
                # Handle text strings (like ESP32 firmware text processing)
                elif isinstance(element, str):
                    # Filter QR URL text (like ESP32 firmware)
                    if element.startswith("QR:"):
                        logger.debug(f"🚫 Filtered QR URL text: {element}")
                        continue  # Skip this line - don't print QR URLs as text
                    
                    # Apply current persistent formatting before printing text (like ESP32)
                    self._apply_current_format()
                    self._print_text_line(element)
                    logger.debug(f"📝 Text printed with format - Align: {self.formatter.current_align}, Bold: {self.formatter.current_bold}, Size: {self.formatter.current_size}")

            # Finalize receipt (cut paper, add spacing) - THIS WAS MISSING!
            self._finalize_receipt()
            
            # Flush any remaining print data
            self._flush_print_job()
            
            logger.debug("✅ Receipt printing completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Print receipt error: {str(e)}")
            import traceback
            logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            return False

    def _apply_short_format(self, element: dict):
        """
        Apply short format changes exactly like ESP32 firmware applyShortFormat.
        
        Args:
            element: JSON object with 'f' formatting key
        """
        if "f" not in element:
            return
            
        fmt = element["f"]
        changes = {}
        
        # Handle alignment (like ESP32 firmware)
        if "a" in fmt:
            align_char = fmt["a"]
            # Handle both uppercase and lowercase alignment codes (like ESP32)
            if align_char.lower() == 'c':
                align_char = 'C'
            elif align_char.lower() == 'l':
                align_char = 'L'
            elif align_char.lower() == 'r':
                align_char = 'R'
            
            if align_char != self.formatter.current_align:
                self.formatter.current_align = align_char
                changes["align"] = align_char
                logger.debug(f"🎨 Format: Alignment changed to {align_char}")
        
        # Handle bold (like ESP32 firmware)
        if "b" in fmt:
            bold_val = fmt["b"]
            if bold_val != self.formatter.current_bold:
                self.formatter.current_bold = bold_val
                changes["bold"] = bold_val
                logger.debug(f"🎨 Format: Bold changed to {'ON' if bold_val else 'OFF'}")
        
        # Handle size (like ESP32 firmware)
        if "s" in fmt:
            size_val = fmt["s"]
            if size_val != self.formatter.current_size:
                self.formatter.current_size = size_val
                changes["size"] = size_val
                logger.debug(f"🎨 Format: Size changed to {size_val}")
        
        # Apply changes to printer immediately (like ESP32 firmware)
        if changes:
            self._apply_current_format()

    def _apply_current_format(self):
        """
        Apply current persistent formatting state to printer (like ESP32 applyCurrentFormat).
        """
        # Set alignment
        if self.formatter.current_align == 'C':
            self.printer.set_with_default(align='center')
        elif self.formatter.current_align == 'R':
            self.printer.set_with_default(align='right')
        else:
            self.printer.set_with_default(align='left')

        # Set bold
        if self.formatter.current_bold:
            self.printer.set_with_default(bold=True)
        else:
            self.printer.set_with_default(bold=False)

        # Set size
        if self.formatter.current_size == 2:
            self.printer.set_with_default(double_height=True, double_width=True)
        elif self.formatter.current_size == 0:
            self.printer.set_with_default(double_height=False, double_width=False, width=1, height=1)
        else:
            self.printer.set_with_default(double_height=False, double_width=False)

    def _print_text_line(self, text: str):
        """Print a text line with current formatting (like ESP32 firmware)."""
        if not text:
            # Empty line
            self.printer.text("\n")
            return

        # Apply current persistent formatting state (like ESP32 applyCurrentFormat())
        self._apply_current_format()
        
        # Print text with line ending
        self.printer.text(text + "\n")
        
        logger.debug(f"📝 Text printed with format - Align: {self.formatter.current_align}, "
                    f"Bold: {'ON' if self.formatter.current_bold else 'OFF'}, "
                    f"Size: {self.formatter.current_size}")

    def _apply_format(self, format_element: Dict[str, Any]):
        """Apply formatting changes (like ESP32 firmware applyShortFormat)."""
        changes = self.formatter.apply_format(format_element)
        
        # Log format changes like ESP32 firmware
        if changes:
            if "align" in changes:
                logger.debug(f"🎨 Format: Alignment changed to {changes['align']}")
            if "bold" in changes:
                logger.debug(f"🎨 Format: Bold changed to {'ON' if changes['bold'] else 'OFF'}")
            if "size" in changes:
                logger.debug(f"🎨 Format: Size changed to {changes['size']}")
        
        # Apply changes to printer immediately (persistent formatting)
        if changes:
            self._apply_current_format()
            
        logger.debug(f"🎨 Format applied", changes=changes)

    def _print_line(self, line_element):
        """Print line elements using proper ESC/POS bitmap commands like ESP32 firmware."""
        try:
            line_type = line_element.get("line", "solid")
            logger.debug(f"📏 Drawing line type: {line_type}")
            
            if line_type == "solid":
                self._print_solid_line_bitmap()
            elif line_type == "dotted":
                self._print_dotted_line_bitmap()
            elif line_type == "dashed":
                self._print_dashed_line_bitmap()
            else:
                logger.warning(f"Unknown line type: {line_type}, using solid")
                self._print_solid_line_bitmap()
                
        except Exception as e:
            logger.error(f"Error printing line: {e}")
            # Fallback to simple text line
            self.printer.text("--------------------------------\n")

    def _print_solid_line_bitmap(self):
        """Print solid line using ESC/POS bitmap command like ESP32 firmware."""
        try:
            logger.debug("📏 Drawing solid line using ESC/POS bitmap")
            
            # Use full 80mm printer width (72 bytes = 576 pixels)
            bytes_per_row = 72
            thickness = 2  # 2 pixel thick line
            
            # Create bitmap data for solid line (all pixels black)
            total_bytes = bytes_per_row * thickness
            line_data = bytearray([0xFF] * total_bytes)  # 0xFF = all pixels black
            
            # Add spacing above
            self.printer.text("\n")
            
            # Send ESC/POS raster bitmap command: GS v 0
            cmd = bytes([0x1D, ord('v'), ord('0'), 0, bytes_per_row, 0, thickness, 0])
            self.printer._raw(cmd)
            
            # Send bitmap data
            self.printer._raw(line_data)
            
            # Add spacing below
            self.printer.text("\n")
            
            logger.debug("✅ Solid line printed using ESC/POS bitmap")
            
        except Exception as e:
            logger.error(f"Error printing solid line bitmap: {e}")
            # Fallback to text line
            self.printer.text("=" * 48 + "\n")

    def _print_dotted_line_bitmap(self):
        """Print dotted line using ESC/POS bitmap command like ESP32 firmware."""
        try:
            logger.debug("📏 Drawing dotted line using ESC/POS bitmap")
            
            # Use full 80mm printer width
            bytes_per_row = 72
            dot_size = 2      # 2 pixel dots
            spacing = 2       # 2 pixel spacing between dots
            
            total_bytes = bytes_per_row * dot_size
            line_data = bytearray([0x00] * total_bytes)  # Start with all white
            
            # Create dotted pattern
            pattern_length = dot_size + spacing
            for row in range(dot_size):
                for col in range(bytes_per_row):
                    byte_index = row * bytes_per_row + col
                    
                    # Create pattern: dot_size pixels on, spacing pixels off
                    for bit in range(8):
                        pixel_pos = (col * 8 + bit) % pattern_length
                        if pixel_pos < dot_size:
                            line_data[byte_index] |= (0x80 >> bit)  # Set bit (black pixel)
            
            # Add spacing above
            self.printer.text("\n")
            
            # Send ESC/POS raster bitmap command: GS v 0
            cmd = bytes([0x1D, ord('v'), ord('0'), 0, bytes_per_row, 0, dot_size, 0])
            self.printer._raw(cmd)
            
            # Send bitmap data
            self.printer._raw(line_data)
            
            # Add spacing below
            self.printer.text("\n")
            
            logger.debug("✅ Dotted line printed using ESC/POS bitmap")
            
        except Exception as e:
            logger.error(f"Error printing dotted line bitmap: {e}")
            # Fallback to text line
            self.printer.text("." * 24 + " " * 24 + "\n")

    def _print_dashed_line_bitmap(self):
        """Print dashed line using simple text characters as fallback."""
        try:
            logger.debug("📏 Drawing dashed line using text characters")
            self.printer.text("- " * 24 + "\n")
            logger.debug("✅ Dashed line printed")
        except Exception as e:
            logger.error(f"Error printing dashed line: {e}")
            self.printer.text("--------------------------------\n")

    def _print_qr_code(self, qr_element):
        """Print QR code using the method that works in ESP32 firmware."""
        try:
            logger.debug(f"🔲 Processing QR element: {qr_element}")
            
            # Handle different QR formats from server
            if "url" in qr_element:
                # This is the format created by the main processing loop
                qr_url = qr_element["url"]
                qr_size = qr_element.get("size", 10)
                qr_alignment = qr_element.get("alignment", "center")
                
                logger.debug(f"🌐 QR URL detected: {qr_url}")
                logger.debug(f"🔲 QR size: {qr_size}, alignment: {qr_alignment}")
                
                # Use the built-in ESC/POS QR method like ESP32 firmware
                success = self._print_qr_code_builtin(qr_url, qr_size, qr_alignment)
                
                if not success:
                    logger.warning("QR code printing failed - printing fallback text")
                    self.printer.text("QR Code Unavailable\n")
                    self.printer.text("Contact theater for details\n")
                else:
                    logger.debug("✅ QR code printed successfully")
                    
            elif "qr_url" in qr_element:
                # Direct QR URL format
                qr_url = qr_element["qr_url"]
                qr_size = qr_element.get("qr_size", 10)
                qr_alignment = qr_element.get("qr_alignment", "center")
                
                logger.debug(f"🌐 Direct QR URL detected: {qr_url}")
                success = self._print_qr_code_builtin(qr_url, qr_size, qr_alignment)
                
                if not success:
                    self.printer.text("QR Code Unavailable\n")
                    
            elif "qr" in qr_element:
                # Legacy QR format
                qr_data = qr_element["qr"]
                logger.debug(f"🔲 Legacy QR format: {qr_data}")
                success = self._print_qr_code_builtin(qr_data, 10, "center")
                
                if not success:
                    self.printer.text("QR Code Unavailable\n")
                    
            elif "text" in qr_element:
                # Text-based QR format
                qr_text = qr_element["text"]
                qr_size = qr_element.get("size", 10)
                qr_alignment = qr_element.get("alignment", "center")
                
                logger.debug(f"🔲 Text QR format: {qr_text}")
                success = self._print_qr_code_builtin(qr_text, qr_size, qr_alignment)
                
                if not success:
                    self.printer.text("QR Code Unavailable\n")
                    
            else:
                logger.warning(f"Unknown QR element format: {qr_element}")
                self.printer.text("QR Code Format Error\n")
                
        except Exception as e:
            logger.error(f"Error printing QR code: {e}")
            self.printer.text("QR Code Error\n")

    def _print_qr_code_builtin(self, data, size=10, alignment="center"):
        """
        Print QR code using built-in ESC/POS QR commands like ESP32 firmware.
        This is the method that actually works in the ESP32 firmware.
        """
        try:
            logger.debug(f"🔲 Printing QR using built-in ESC/POS method")
            logger.debug(f"🔲 Data: {data}")
            logger.debug(f"🔲 Size: {size}, Alignment: {alignment}")
            
            # Map alignment to ESC/POS codes
            align_code = 1  # Center by default
            if alignment == "left":
                align_code = 0
            elif alignment == "right":
                align_code = 2
            elif alignment == "center":
                align_code = 1
            
            # Set alignment
            self.printer._raw(bytes([0x1B, ord('a'), align_code]))
            
            # Map UI size to thermal printer QR size (like ESP32 firmware)
            thermal_size = size
            if size <= 4:
                thermal_size = 3   # Small
            elif size <= 8:
                thermal_size = 6   # Medium  
            elif size <= 12:
                thermal_size = 10  # Large
            else:
                thermal_size = 12  # Extra Large
                
            # Validate size range (1-16 for most thermal printers)
            if thermal_size < 1:
                thermal_size = 1
            if thermal_size > 16:
                thermal_size = 16
                
            logger.debug(f"🔲 Mapped size {size} to thermal size {thermal_size}")
            
            # Validate data length
            data_bytes = data.encode('utf-8')
            if len(data_bytes) > 200:
                logger.warning("QR data too long, truncating to 200 bytes")
                data_bytes = data_bytes[:200]
            
            # ESC/POS QR Code commands (like ESP32 firmware)
            cn = 49  # QR Code function group
            
            # Set QR code size (Function 167)
            size_cmd = bytes([0x1D, ord('('), ord('k'), 0x03, 0x00, cn, 167, thermal_size])
            self.printer._raw(size_cmd)
            
            # Set error correction level (Function 169) - Level H (30%)
            error_cmd = bytes([0x1D, ord('('), ord('k'), 0x03, 0x00, cn, 169, 0x33])
            self.printer._raw(error_cmd)
            
            # Store QR data (Function 180)
            data_len = len(data_bytes)
            store_cmd = bytes([0x1D, ord('('), ord('k'), 
                             (data_len + 3) & 0xFF, ((data_len + 3) >> 8) & 0xFF,
                             cn, 180, 0x30]) + data_bytes
            self.printer._raw(store_cmd)
            
            # Print QR code (Function 181)
            print_cmd = bytes([0x1D, ord('('), ord('k'), 0x03, 0x00, cn, 181, 0x30])
            self.printer._raw(print_cmd)
            
            # Add some spacing after QR code
            self.printer.text("\n\n")
            
            # Reset alignment to left
            self.printer._raw(bytes([0x1B, ord('a'), 0]))
            
            logger.debug("✅ Built-in ESC/POS QR code printed")
            return True
            
        except Exception as e:
            logger.error(f"Error printing built-in QR code: {e}")
            return False

    def _print_qr_url_real(self, qr_data: Dict[str, Any]) -> bool:
        """Generate and print actual QR code from URL like ESP32 firmware should do."""
        try:
            import qrcode
            from PIL import Image
            import io
            
            # Get URL from QR data
            url = qr_data.get("url", qr_data.get("text", ""))
            if not url:
                logger.error("❌ No URL provided for QR code")
                return False
                
            logger.debug(f"🔲 Generating QR code for URL: {url}")
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,  # Smaller box size for thermal printer
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bitmap for thermal printer
            # Resize to appropriate size for thermal printer
            width, height = img.size
            if width > 200:  # Limit size for thermal printer
                ratio = 200 / width
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.NEAREST)
            
            # Convert to 1-bit bitmap
            img = img.convert('1')
            
            # Convert to bytes for ESC/POS
            width, height = img.size
            bytes_per_row = (width + 7) // 8
            bitmap_data = []
            
            # Convert PIL image to bitmap bytes (proper ESC/POS format)
            for y in range(height):
                for byte_idx in range(bytes_per_row):
                    byte_val = 0
                    for bit in range(8):
                        x = byte_idx * 8 + bit
                        if x < width:
                            pixel = img.getpixel((x, y))
                            if pixel == 0:  # Black pixel (0 in 1-bit image)
                                byte_val |= (0x80 >> bit)
                    bitmap_data.append(byte_val)
            
            # Print bitmap using ESC/POS commands
            logger.debug(f"🔲 Printing QR bitmap: {width}x{height}, {len(bitmap_data)} bytes")
            self.printer.print_bitmap(width, height, bytes(bitmap_data))
            
            logger.debug(f"🔲 Real QR code printed successfully: {width}x{height}")
            return True
            
        except ImportError:
            logger.warning("⚠️ qrcode library not installed, falling back to text")
            self.printer.text(f"QR: {url}\n")
            return False
        except Exception as e:
            logger.error(f"❌ QR generation error: {str(e)}")
            self.printer.text(f"QR: {url}\n")
            return False

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

    def _print_qr_url_escpos(self, qr_data: Dict[str, Any]):
        """Print QR code using reliable ESC/POS QR command."""
        try:
            url = qr_data.get("url", qr_data.get("text", ""))
            size = qr_data.get("size", 6)

            # Map size to ESC/POS QR size (1-16)
            escpos_size = max(3, min(10, size))  # Use safe size range

            logger.debug(f"🔲 Printing QR with ESC/POS command: size={escpos_size}")
            
            # Use the NamedPrinterWrapper QR function directly
            self.printer.qr(url, size=escpos_size, center=True)

        except Exception as e:
            logger.error(f"❌ ESC/POS QR print error: {str(e)}")
            # Reliable fallback to text
            self.printer.text(f"\nQR Code: {url}\n")
            self.printer.text("(Scan with phone camera)\n\n")

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
            if hasattr(self.printer, 'cut'):
                self.printer.cut()
                logger.debug("✂️ Paper cut command sent")
            else:
                logger.debug("⚠️ Cut not supported, adding extra space")
                self.printer.text("\n\n\n")
        except Exception as e:
            logger.warning(f"⚠️ Cut failed: {str(e)}, adding extra space")
            self.printer.text("\n\n\n")

    def _flush_print_job(self):
        """Flush the print job to the printer."""
        try:
            if isinstance(self.printer, NamedPrinterWrapper):
                # For named printers, call close to send buffered data
                self.printer.close()
                logger.debug("📤 Print job flushed to named printer")
            elif hasattr(self.printer, 'close'):
                # For USB printers, close might also flush
                # But we don't want to close the connection, just flush
                pass  # USB printers typically auto-flush
            else:
                logger.debug("📤 Print job sent to USB printer")
        except Exception as e:
            logger.error(f"❌ Print flush error: {str(e)}")
            raise

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
            
            # Avoid sending raw commands that might disrupt the connection
            # Instead, just check if the printer object exists and is connected
            if hasattr(self.printer, '_raw'):
                # For USB printers, assume ready if connected
                self.current_status = PrinterStatus.READY
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
    """Wrapper for system printers accessed by name via lp command with ESC/POS support."""

    # ESC/POS command constants
    ESC = 0x1B
    GS = 0x1D
    LF = 0x0A
    CR = 0x0D
    
    def __init__(self, printer_name: str):
        self.printer_name = printer_name
        self._buffer = b""
        
        # Track formatting state like ESP32 firmware
        self.current_align = 'L'  # L=Left, C=Center, R=Right
        self.current_bold = False
        self.current_size = 1     # 1=Normal, 2=Large, 0=Small
        self.current_font = 'A'   # A or B
        
        # Initialize with default settings (done later to avoid issues during construction)
        self._initialized = False

    def init(self):
        """Initialize printer with ESC/POS commands."""
        if self._initialized:
            return
            
        # ESC @ - Initialize printer
        self._raw(bytes([self.ESC, 0x40]))
        
        # Set default formatting
        self.justify('L')
        self.set_size(1)
        self.set_font('A')
        self.bold_off()
        
        self._initialized = True

    def text(self, text: str):
        """Add text to print buffer with current formatting applied."""
        # Ensure printer is initialized
        if not self._initialized:
            self.init()
            
        # Convert text and handle line endings properly
        text_bytes = text.encode('utf-8')
        self._buffer += text_bytes

    def set_with_default(self, **kwargs):
        """Set formatting based on kwargs (compatible with python-escpos)."""
        # Handle alignment
        if 'align' in kwargs:
            align = kwargs['align']
            if align == 'center':
                self.justify('C')
            elif align == 'right':
                self.justify('R')
            else:
                self.justify('L')
        
        # Handle bold
        if 'bold' in kwargs:
            if kwargs['bold']:
                self.bold_on()
            else:
                self.bold_off()
        
        # Handle size (double width/height)
        if 'double_height' in kwargs or 'double_width' in kwargs:
            double_height = kwargs.get('double_height', False)
            double_width = kwargs.get('double_width', False)
            
            if double_height and double_width:
                self.set_size(2)  # Large
            elif double_height or double_width:
                self.set_size(1)  # Medium (normal with one dimension doubled)
            else:
                self.set_size(1)  # Normal

    def justify(self, alignment: str):
        """Set text alignment using ESC/POS commands."""
        alignment = alignment.upper()
        if alignment != self.current_align:
            self.current_align = alignment
            
            # ESC a n - Set justification
            if alignment == 'C':
                self._raw(bytes([self.ESC, ord('a'), 0x01]))  # Center
            elif alignment == 'R':
                self._raw(bytes([self.ESC, ord('a'), 0x02]))  # Right
            else:
                self._raw(bytes([self.ESC, ord('a'), 0x00]))  # Left

    def bold_on(self):
        """Turn on bold text."""
        if not self.current_bold:
            self.current_bold = True
            # ESC E 1 - Turn on bold
            self._raw(bytes([self.ESC, ord('E'), 0x01]))

    def bold_off(self):
        """Turn off bold text."""
        if self.current_bold:
            self.current_bold = False
            # ESC E 0 - Turn off bold
            self._raw(bytes([self.ESC, ord('E'), 0x00]))

    def set_size(self, size: int):
        """Set text size using ESC/POS commands."""
        if size != self.current_size:
            self.current_size = size
            
            # GS ! n - Set character size
            if size == 2:
                # Large: double width and height
                self._raw(bytes([self.GS, ord('!'), 0x11]))
            elif size == 0:
                # Small: normal size (some printers support smaller fonts)
                self._raw(bytes([self.GS, ord('!'), 0x00]))
            else:
                # Normal size
                self._raw(bytes([self.GS, ord('!'), 0x00]))

    def set_font(self, font: str):
        """Set font type."""
        font = font.upper()
        if font != self.current_font:
            self.current_font = font
            
            # ESC M n - Set font
            if font == 'B':
                self._raw(bytes([self.ESC, ord('M'), 0x01]))
            else:
                self._raw(bytes([self.ESC, ord('M'), 0x00]))

    def _apply_current_formatting(self):
        """Apply current formatting state (like ESP32 firmware applyCurrentFormat)."""
        # This ensures formatting is applied before each text output
        # Similar to ESP32 firmware's applyCurrentFormat() function
        pass  # Formatting is already applied when state changes

    def qr(self, text: str, size: int = 6, center: bool = True):
        """Print QR code using ESC/POS QR commands or fallback to text."""
        try:
            # Center QR code if requested
            if center:
                old_align = self.current_align
                self.justify('C')
            
            # Try ESC/POS QR code command
            # GS ( k - QR Code commands
            text_bytes = text.encode('utf-8')
            text_len = len(text_bytes)
            
            # QR Code model
            self._raw(bytes([self.GS, ord('('), ord('k'), 4, 0, 49, 65, 50, 0]))
            
            # QR Code size
            qr_size = max(1, min(16, size))
            self._raw(bytes([self.GS, ord('('), ord('k'), 3, 0, 49, 67, qr_size]))
            
            # QR Code error correction level
            self._raw(bytes([self.GS, ord('('), ord('k'), 3, 0, 49, 69, 48]))
            
            # QR Code data
            self._raw(bytes([self.GS, ord('('), ord('k'), text_len + 3, 0, 49, 80, 48]))
            self._raw(text_bytes)
            
            # Print QR Code
            self._raw(bytes([self.GS, ord('('), ord('k'), 3, 0, 49, 81, 48]))
            
            # Add some spacing
            self._raw(bytes([self.LF, self.LF]))
            
            # Restore alignment
            if center and old_align != 'C':
                self.justify(old_align)
                
        except Exception as e:
            logger.debug(f"QR command failed, using text fallback: {str(e)}")
            # Fallback to text representation
            if center:
                self.text(f"\n    QR: {text}\n\n")
            else:
                self.text(f"QR: {text}\n")

    def print_bitmap(self, width: int, height: int, bitmap_data: bytes):
        """Print bitmap using ESC/POS commands."""
        # Ensure printer is initialized
        if not self._initialized:
            self.init()
        
        # Add DC2 constant if not defined
        DC2 = 0x12
        
        # Calculate bytes per row
        bytes_per_row = (width + 7) // 8
        
        # Print bitmap in chunks to avoid buffer overflow
        chunk_height = min(height, 255)
        
        for y_start in range(0, height, chunk_height):
            current_chunk_height = min(chunk_height, height - y_start)
            
            # ESC/POS bitmap command: DC2 * height width
            self._raw(bytes([DC2, 0x2A, current_chunk_height, bytes_per_row]))
            
            # Send bitmap data for this chunk
            for y in range(current_chunk_height):
                row_start = (y_start + y) * bytes_per_row
                row_end = row_start + bytes_per_row
                if row_end <= len(bitmap_data):
                    self._raw(bitmap_data[row_start:row_end])
                else:
                    # Pad with zeros if data is insufficient
                    remaining_data = bitmap_data[row_start:len(bitmap_data)]
                    padding = bytes(bytes_per_row - len(remaining_data))
                    self._raw(remaining_data + padding)
    
    def print_solid_line(self, thickness: int = 2, width: int = 48):
        """Print solid line using bitmap graphics like ESP32 firmware."""
        DC2 = 0x12
        
        # Use full width for 80mm thermal printer
        bytes_per_row = 48  # 384 pixels = 48 bytes
        
        # Create solid line bitmap
        line_data = bytes([0xFF] * (bytes_per_row * thickness))
        
        # Print using bitmap command
        self._raw(bytes([DC2, 0x2A, thickness, bytes_per_row]))
        self._raw(line_data)
        
        # Add line feed
        self._raw(bytes([self.LF]))
    
    def print_dotted_line(self, dot_size: int = 2, spacing: int = 2, width: int = 48):
        """Print dotted line using bitmap graphics like ESP32 firmware."""
        DC2 = 0x12
        bytes_per_row = 48  # 384 pixels = 48 bytes
        
        # Create dotted pattern
        pattern_length = dot_size + spacing
        line_data = bytearray(bytes_per_row * dot_size)
        
        for row in range(dot_size):
            for col in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    pixel_pos = (col * 8 + bit) % pattern_length
                    if pixel_pos < dot_size:
                        byte_val |= (0x80 >> bit)
                line_data[row * bytes_per_row + col] = byte_val
        
        # Print using bitmap command
        self._raw(bytes([DC2, 0x2A, dot_size, bytes_per_row]))
        self._raw(bytes(line_data))
        
        # Add line feed
        self._raw(bytes([self.LF]))
    
    def feed(self, lines: int = 1):
        """Feed paper by specified number of lines."""
        for _ in range(lines):
            self._raw(bytes([self.LF]))

    def cut(self):
        """Cut paper using multiple ESC/POS cut commands for better compatibility."""
        # Add some space before cutting
        self._raw(bytes([self.LF, self.LF, self.LF]))
        
        # Try multiple cut commands for better compatibility
        try:
            # Method 1: GS V 0 - Full cut
            self._raw(bytes([self.GS, ord('V'), 0x00]))
        except:
            pass
        
        try:
            # Method 2: GS V 1 - Partial cut (more compatible)
            self._raw(bytes([self.GS, ord('V'), 0x01]))
        except:
            pass
        
        try:
            # Method 3: ESC d n - Feed and cut
            self._raw(bytes([self.ESC, ord('d'), 3]))
        except:
            pass
        
        # Add more space to ensure cut happens
        self._raw(bytes([self.LF, self.LF, self.LF]))

    def _raw(self, data: bytes):
        """Send raw data to printer buffer."""
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
                logger.info(f"✅ Print job sent to printer: {self.printer_name}")
                self._buffer = b""
            except Exception as e:
                logger.error(f"❌ lp print error: {str(e)}")
                raise


# Global printer manager instance
printer_manager = USBPrinterManager()
