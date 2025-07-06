"""
QR code generation for SD MQTT Printer Mac client.
Handles QR code generation compatible with ESP32 firmware formats.
"""

import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
import io

from config import config
from utils.logger import logger
from utils.bitmap import encode_pixel_array_to_bitmap, analyze_bitmap_density


class QRGenerator:
    """QR code generator with ESP32 firmware compatibility."""

    def __init__(self):
        self.error_correction_map = {
            'L': ERROR_CORRECT_L,
            'M': ERROR_CORRECT_M,
            'Q': ERROR_CORRECT_Q,
            'H': ERROR_CORRECT_H
        }

    def generate_qr_bitmap(self, url: str, size: int = 10, alignment: str = "center") -> Dict[str, Any]:
        """
        Generate QR code bitmap compatible with ESP32 firmware format.

        Args:
            url: URL or text to encode
            size: QR size (1-16, maps to pixel sizes)
            alignment: QR alignment (left, center, right)

        Returns:
            QR bitmap data in ESP32 firmware format
        """
        logger.qr_generated(url, size)

        # Map size to pixel dimensions
        pixel_size = self._map_size_to_pixels(size)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=self.error_correction_map[config.QR_ERROR_CORRECTION],
            box_size=config.QR_BOX_SIZE,
            border=config.QR_BORDER,
        )

        qr.add_data(url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Resize to target size
        img = img.resize((pixel_size, pixel_size), Image.NEAREST)

        # Convert to bitmap data
        bitmap_data = self._image_to_bitmap(img)

        # Analyze bitmap
        analysis = analyze_bitmap_density(bitmap_data, pixel_size, pixel_size)

        logger.debug(f"🔲 QR bitmap generated",
                    size=f"{pixel_size}x{pixel_size}",
                    black_percentage=f"{analysis['black_percentage']:.1f}%",
                    bitmap_bytes=len(bitmap_data))

        # Return in ESP32 firmware format
        return {
            "qr_bitmap": {
                "width": pixel_size,
                "height": pixel_size,
                "data": bitmap_data,
                "encoding": "bitmap_1bit_packed",
                "format": "thermal_printer_optimized",
                "timestamp": int(config.HEARTBEAT_INTERVAL * 1000)  # Use config timestamp
            },
            "qr_size": size,
            "qr_alignment": alignment
        }

    def generate_qr_url_format(self, url: str, size: int = 10, alignment: str = "center") -> Dict[str, Any]:
        """
        Generate QR code in URL format for ESP32 firmware.

        Args:
            url: URL to encode
            size: QR size (1-16)
            alignment: QR alignment

        Returns:
            QR URL data in ESP32 firmware format
        """
        logger.qr_generated(url, size)

        return {
            "qr_url": url,
            "qr_size": size,
            "qr_alignment": alignment
        }

    def _map_size_to_pixels(self, size: int) -> int:
        """
        Map QR size (1-16) to pixel dimensions.
        Compatible with ESP32 firmware size mapping.
        """
        if size <= 3:
            return 64   # Small
        elif size <= 6:
            return 96   # Medium
        elif size <= 10:
            return 128  # Large
        elif size <= 12:
            return 160  # Extra Large
        else:
            return 192  # Maximum

    def _image_to_bitmap(self, img: Image.Image) -> List[int]:
        """
        Convert PIL Image to bit-packed bitmap data.

        Args:
            img: PIL Image (should be black and white)

        Returns:
            Bit-packed bitmap data
        """
        # Convert to grayscale if needed
        if img.mode != 'L':
            img = img.convert('L')

        # Get pixel data
        pixels = list(img.getdata())

        # Convert to bitmap
        width, height = img.size
        bitmap_data = encode_pixel_array_to_bitmap(pixels, width, height)

        return bitmap_data

    def generate_wifi_qr(self, ssid: str, password: str, security: str = "WPA") -> Dict[str, Any]:
        """
        Generate WiFi QR code.

        Args:
            ssid: WiFi network name
            password: WiFi password
            security: Security type (WPA, WEP, nopass)

        Returns:
            WiFi QR bitmap data
        """
        wifi_string = f"WIFI:T:{security};S:{ssid};P:{password};;"

        logger.debug(f"🔲 Generating WiFi QR",
                    ssid=ssid,
                    security=security)

        return self.generate_qr_bitmap(wifi_string, size=10, alignment="center")

    def generate_order_qr(self, order_id: str, whatsapp_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate order QR code.

        Args:
            order_id: Order ID
            whatsapp_phone: WhatsApp phone number (optional)

        Returns:
            Order QR bitmap data
        """
        if whatsapp_phone:
            # WhatsApp format
            whatsapp_text = f"__order {order_id}"
            url = f"https://wa.me/{whatsapp_phone}?text={whatsapp_text}"
        else:
            # Web URL format
            url = f"https://scandeer.com/order/{order_id}"

        logger.debug(f"🔲 Generating order QR",
                    order_id=order_id,
                    url=url[:50] + "..." if len(url) > 50 else url)

        return self.generate_qr_bitmap(url, size=10, alignment="center")

    def validate_qr_bitmap(self, qr_data: Dict[str, Any]) -> bool:
        """
        Validate QR bitmap data structure.

        Args:
            qr_data: QR bitmap data

        Returns:
            True if valid, False otherwise
        """
        try:
            if "qr_bitmap" not in qr_data:
                return False

            bitmap = qr_data["qr_bitmap"]

            # Check required fields
            required_fields = ["width", "height", "data"]
            for field in required_fields:
                if field not in bitmap:
                    logger.error(f"❌ Missing QR bitmap field: {field}")
                    return False

            width = bitmap["width"]
            height = bitmap["height"]
            data = bitmap["data"]

            # Validate dimensions
            if width <= 0 or height <= 0:
                logger.error(f"❌ Invalid QR dimensions: {width}x{height}")
                return False

            if width > 256 or height > 256:
                logger.error(f"❌ QR too large: {width}x{height}")
                return False

            # Validate data size
            expected_size = (width + 7) // 8 * height
            if len(data) != expected_size:
                logger.error(f"❌ QR data size mismatch: {len(data)} vs {expected_size}")
                return False

            # Validate data values
            for i, byte_val in enumerate(data):
                if not isinstance(byte_val, int) or byte_val < 0 or byte_val > 255:
                    logger.error(f"❌ Invalid QR data byte at {i}: {byte_val}")
                    return False

            logger.debug(f"✅ QR bitmap validation passed",
                        size=f"{width}x{height}",
                        data_bytes=len(data))

            return True

        except Exception as e:
            logger.error(f"❌ QR bitmap validation error: {str(e)}")
            return False

    def create_test_qr(self) -> Dict[str, Any]:
        """
        Create a test QR code for debugging.

        Returns:
            Test QR bitmap data
        """
        test_url = "https://scandeer.com/test"
        return self.generate_qr_bitmap(test_url, size=8, alignment="center")


# Global QR generator instance
qr_generator = QRGenerator()
