"""
Text formatting utilities for SD MQTT Printer Mac client.
Handles ESP32 firmware format compatibility and text processing.
"""

from typing import Dict, Any, Optional


class PrinterFormatter:
    """
    Handles formatting commands compatible with ESP32 firmware.
    Maintains state for alignment, bold, size, etc.
    """

    def __init__(self):
        self.reset_formatting()

    def reset_formatting(self):
        """Reset all formatting to defaults."""
        self.current_align = 'L'  # L=Left, C=Center, R=Right
        self.current_bold = False
        self.current_size = 1     # 1=Normal, 2=Large, 0=Small
        self.current_italic = False
        self.current_underline = False

    def apply_format(self, format_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply format object from ESP32 firmware format.

        Format object structure:
        {
            "f": {
                "a": "c",  # alignment: l/c/r
                "b": 1,    # bold: 0/1 or true/false
                "s": 2,    # size: 0/1/2
                "i": 1,    # italic: 0/1 or true/false
                "u": 1     # underline: 0/1 or true/false
            }
        }
        """
        if "f" not in format_obj:
            return {}

        fmt = format_obj["f"]
        changes = {}

        # Handle alignment
        if "a" in fmt:
            align = fmt["a"].upper()
            if align in ["L", "C", "R"]:
                if align != self.current_align:
                    self.current_align = align
                    changes["align"] = align

        # Handle bold
        if "b" in fmt:
            bold = self._parse_bool(fmt["b"])
            if bold != self.current_bold:
                self.current_bold = bold
                changes["bold"] = bold

        # Handle size
        if "s" in fmt:
            size = int(fmt["s"])
            if size != self.current_size:
                self.current_size = size
                changes["size"] = size

        # Handle italic
        if "i" in fmt:
            italic = self._parse_bool(fmt["i"])
            if italic != self.current_italic:
                self.current_italic = italic
                changes["italic"] = italic

        # Handle underline
        if "u" in fmt:
            underline = self._parse_bool(fmt["u"])
            if underline != self.current_underline:
                self.current_underline = underline
                changes["underline"] = underline

        return changes

    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean value from various formats."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return value != 0
        elif isinstance(value, str):
            return value.lower() in ["true", "1", "yes", "on"]
        else:
            return False

    def get_current_format(self) -> Dict[str, Any]:
        """Get current formatting state."""
        return {
            "align": self.current_align,
            "bold": self.current_bold,
            "size": self.current_size,
            "italic": self.current_italic,
            "underline": self.current_underline,
        }

    def format_text_for_alignment(self, text: str, width: int = 48) -> str:
        """
        Format text according to current alignment.

        Args:
            text: Text to format
            width: Line width in characters (default 48 for 80mm printer)
        """
        if self.current_align == 'C':
            return text.center(width)
        elif self.current_align == 'R':
            return text.rjust(width)
        else:  # 'L' or default
            return text.ljust(width)


def parse_line_command(line_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse line drawing command from ESP32 firmware format.

    Line object structure:
    {
        "line": "solid"  # or object with type, thickness, width, spacing
    }
    """
    if "line" not in line_obj:
        return {}

    line_data = line_obj["line"]

    if isinstance(line_data, str):
        # Simple string format
        return {
            "type": line_data,
            "thickness": 2,
            "width": 48,
            "spacing": 2
        }
    elif isinstance(line_data, dict):
        # Complex object format
        return {
            "type": line_data.get("type", "solid"),
            "thickness": line_data.get("thickness", 2),
            "width": line_data.get("width", 48),
            "spacing": line_data.get("spacing", 2)
        }
    else:
        return {"type": "solid", "thickness": 2, "width": 48, "spacing": 2}


def parse_qr_command(qr_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse QR code command from ESP32 firmware format.

    QR object structures:
    1. Bitmap format: {"qr_bitmap": {...}}
    2. URL format: {"qr_url": "...", "qr_size": 10, "qr_alignment": "center"}
    3. Legacy format: {"qr": "..."}
    """
    qr_data = None

    # Check for bitmap format
    if "qr_bitmap" in qr_obj:
        bitmap = qr_obj["qr_bitmap"]
        qr_data = {
            "type": "bitmap",
            "width": bitmap.get("width", 96),
            "height": bitmap.get("height", 96),
            "data": bitmap.get("data", []),
            "encoding": bitmap.get("encoding", "bitmap_1bit_packed"),
            "size": qr_obj.get("qr_size", 10),
            "alignment": qr_obj.get("qr_alignment", "center")
        }

    # Check for URL format
    elif "qr_url" in qr_obj:
        qr_data = {
            "type": "url",
            "url": qr_obj["qr_url"],
            "size": qr_obj.get("qr_size", 10),
            "alignment": qr_obj.get("qr_alignment", "center")
        }

    # Check for legacy format
    elif "qr" in qr_obj:
        qr_content = qr_obj["qr"]
        if isinstance(qr_content, str):
            qr_data = {
                "type": "url",
                "url": qr_content,
                "size": 10,
                "alignment": "center"
            }
        elif isinstance(qr_content, dict):
            # Legacy structured format
            if "text" in qr_content:
                qr_data = {
                    "type": "url",
                    "url": qr_content["text"],
                    "size": 10,
                    "alignment": "center"
                }
            elif "url" in qr_content:
                qr_data = {
                    "type": "url",
                    "url": qr_content["url"],
                    "size": 10,
                    "alignment": "center"
                }

    return qr_data


def generate_line_pattern(line_type: str, width: int = 48, thickness: int = 2) -> str:
    """
    Generate line pattern for printing.

    Args:
        line_type: Type of line (solid, dotted, double)
        width: Width in characters
        thickness: Line thickness (number of rows)
    """
    if line_type == "solid":
        return "─" * width
    elif line_type == "dotted":
        return "·" * width
    elif line_type == "double":
        return "═" * width
    else:
        return "-" * width


def replace_variables(text: str, receipt_data: Dict[str, Any]) -> str:
    """
    Replace template variables in text with actual values.
    Compatible with ESP32 firmware variable format.

    Variables format: {{variable_name}}
    """
    if not text or "{{" not in text:
        return text

    # Standard variables mapping
    variables = {
        "business_name": receipt_data.get("business_name", ""),
        "business_address": receipt_data.get("business_address", ""),
        "business_street": receipt_data.get("business_street", ""),
        "business_unit": receipt_data.get("business_unit", ""),
        "business_city": receipt_data.get("business_city", ""),
        "business_state": receipt_data.get("business_state", ""),
        "business_country": receipt_data.get("business_country", ""),
        "business_postal_code": receipt_data.get("business_postal_code", ""),
        "business_phone": receipt_data.get("business_phone", ""),
        "order_id": receipt_data.get("order_id", ""),
        "customer_name": receipt_data.get("customer_name", ""),
        "customer_phone": receipt_data.get("customer_phone", ""),
        "total_amount": receipt_data.get("total_amount", "0.00"),
        "order_time": receipt_data.get("order_time", ""),
        "selected_screen": receipt_data.get("selected_screen", ""),
        "show_time": receipt_data.get("show_time", ""),
        "seat_number": receipt_data.get("seat_number", ""),
    }

    # Replace variables
    result = text
    for var_name, var_value in variables.items():
        placeholder = f"{{{{{var_name}}}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(var_value))

    return result


def format_receipt_items(items: list, characters_per_line: int = 32) -> list:
    """
    Format receipt items for printing.

    Args:
        items: List of order items
        characters_per_line: Maximum characters per line
    """
    formatted_lines = []

    for item in items:
        name = item.get("name", "Unknown Item")
        quantity = item.get("quantity", 1)
        price = item.get("price", 0.00)

        # Format item line
        item_line = f"{name} x{quantity}"
        price_str = f"${price:.2f}"

        # Calculate spacing
        available_space = characters_per_line - len(price_str)
        if len(item_line) > available_space:
            # Truncate item name if too long
            item_line = item_line[:available_space-3] + "..."

        # Right-align price
        line = item_line.ljust(available_space) + price_str
        formatted_lines.append(line)

    return formatted_lines
