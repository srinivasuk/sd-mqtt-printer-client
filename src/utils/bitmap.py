"""
Bitmap processing utilities for SD MQTT Printer Mac client.
Handles QR code bitmap conversion and thermal printer bitmap processing.
"""

from typing import List, Tuple
from PIL import Image
import io


def decode_bit_packed_bitmap(data: List[int], width: int, height: int) -> List[int]:
    """
    Decode bit-packed bitmap data to pixel array.

    Args:
        data: Bit-packed bitmap data (each byte contains 8 pixels)
        width: Bitmap width in pixels
        height: Bitmap height in pixels

    Returns:
        List of pixel values (0=black, 255=white)
    """
    pixels = []
    bytes_per_row = (width + 7) // 8

    for y in range(height):
        for x in range(width):
            byte_index = y * bytes_per_row + (x // 8)
            bit_index = 7 - (x % 8)  # MSB first

            if byte_index < len(data):
                byte_value = data[byte_index]
                is_black = (byte_value & (1 << bit_index)) != 0
                pixels.append(0 if is_black else 255)
            else:
                pixels.append(255)  # Default to white if out of bounds

    return pixels


def encode_pixel_array_to_bitmap(pixels: List[int], width: int, height: int) -> List[int]:
    """
    Encode pixel array to bit-packed bitmap data.

    Args:
        pixels: List of pixel values (0=black, 255=white)
        width: Bitmap width in pixels
        height: Bitmap height in pixels

    Returns:
        Bit-packed bitmap data
    """
    bytes_per_row = (width + 7) // 8
    bitmap_data = [0] * (bytes_per_row * height)

    for y in range(height):
        for x in range(width):
            pixel_index = y * width + x
            if pixel_index < len(pixels):
                is_black = pixels[pixel_index] < 128  # Threshold at 128

                if is_black:
                    byte_index = y * bytes_per_row + (x // 8)
                    bit_index = 7 - (x % 8)  # MSB first
                    bitmap_data[byte_index] |= (1 << bit_index)

    return bitmap_data


def convert_bitmap_to_escpos(bitmap_data: List[int], width: int, height: int) -> bytes:
    """
    Convert bitmap data to ESC/POS format for thermal printers.

    Args:
        bitmap_data: Bit-packed bitmap data
        width: Bitmap width in pixels
        height: Bitmap height in pixels

    Returns:
        ESC/POS bitmap command bytes
    """
    # ESC/POS bitmap command: ESC * m nL nH d1...dk
    # m = mode (0 = 8-dot single-density)
    # nL, nH = number of columns (little-endian)
    # d1...dk = bitmap data

    bytes_per_row = (width + 7) // 8

    # Build ESC/POS command
    command = bytearray()

    # Process bitmap row by row (8 dots high per command)
    for row_group in range(0, height, 8):
        rows_in_group = min(8, height - row_group)

        # ESC * command
        command.extend(b'\x1B*')  # ESC *
        command.append(0)         # Single-density mode
        command.append(width & 0xFF)      # nL (width low byte)
        command.append((width >> 8) & 0xFF)  # nH (width high byte)

        # Process each column
        for col in range(width):
            column_byte = 0

            # Pack 8 vertical pixels into one byte
            for bit in range(rows_in_group):
                row = row_group + bit
                if row < height:
                    byte_index = row * bytes_per_row + (col // 8)
                    bit_index = 7 - (col % 8)

                    if byte_index < len(bitmap_data):
                        pixel_is_black = (bitmap_data[byte_index] & (1 << bit_index)) != 0
                        if pixel_is_black:
                            column_byte |= (1 << bit)

            command.append(column_byte)

        # Line feed after each row group
        command.extend(b'\x0A')  # LF

    return bytes(command)


def scale_bitmap(bitmap_data: List[int], width: int, height: int, scale_factor: int) -> Tuple[List[int], int, int]:
    """
    Scale bitmap by integer factor.

    Args:
        bitmap_data: Original bitmap data
        width: Original width
        height: Original height
        scale_factor: Scale factor (e.g., 2 for 2x scaling)

    Returns:
        Tuple of (scaled_bitmap_data, new_width, new_height)
    """
    new_width = width * scale_factor
    new_height = height * scale_factor

    # Decode original bitmap to pixels
    pixels = decode_bit_packed_bitmap(bitmap_data, width, height)

    # Scale pixels
    scaled_pixels = []
    for y in range(new_height):
        for x in range(new_width):
            orig_x = x // scale_factor
            orig_y = y // scale_factor
            orig_index = orig_y * width + orig_x
            if orig_index < len(pixels):
                scaled_pixels.append(pixels[orig_index])
            else:
                scaled_pixels.append(255)  # White

    # Encode back to bitmap
    scaled_bitmap = encode_pixel_array_to_bitmap(scaled_pixels, new_width, new_height)

    return scaled_bitmap, new_width, new_height


def create_test_bitmap(width: int = 64, height: int = 64) -> List[int]:
    """
    Create a test bitmap pattern for debugging.

    Args:
        width: Bitmap width
        height: Bitmap height

    Returns:
        Test bitmap data
    """
    pixels = []

    for y in range(height):
        for x in range(width):
            # Create a simple test pattern
            is_black = False

            # Border
            if x == 0 or x == width-1 or y == 0 or y == height-1:
                is_black = True
            # Diagonal lines
            elif x == y or x == (width - 1 - y):
                is_black = True
            # Checkerboard in center
            elif (width//4 < x < 3*width//4) and (height//4 < y < 3*height//4):
                is_black = ((x // 4) + (y // 4)) % 2 == 0

            pixels.append(0 if is_black else 255)

    return encode_pixel_array_to_bitmap(pixels, width, height)


def bitmap_to_pil_image(bitmap_data: List[int], width: int, height: int) -> Image.Image:
    """
    Convert bitmap data to PIL Image for debugging/preview.

    Args:
        bitmap_data: Bit-packed bitmap data
        width: Bitmap width
        height: Bitmap height

    Returns:
        PIL Image object
    """
    pixels = decode_bit_packed_bitmap(bitmap_data, width, height)

    # Create PIL Image
    img = Image.new('L', (width, height))
    img.putdata(pixels)

    return img


def analyze_bitmap_density(bitmap_data: List[int], width: int, height: int) -> dict:
    """
    Analyze bitmap density and characteristics.

    Args:
        bitmap_data: Bit-packed bitmap data
        width: Bitmap width
        height: Bitmap height

    Returns:
        Dictionary with analysis results
    """
    pixels = decode_bit_packed_bitmap(bitmap_data, width, height)

    black_pixels = sum(1 for p in pixels if p < 128)
    white_pixels = len(pixels) - black_pixels

    black_percentage = (black_pixels / len(pixels)) * 100

    # Analyze different regions
    center_x, center_y = width // 2, height // 2
    quarter_size = min(width, height) // 4

    # Center region
    center_black = 0
    center_total = 0
    for y in range(max(0, center_y - quarter_size), min(height, center_y + quarter_size)):
        for x in range(max(0, center_x - quarter_size), min(width, center_x + quarter_size)):
            pixel_index = y * width + x
            if pixel_index < len(pixels):
                center_total += 1
                if pixels[pixel_index] < 128:
                    center_black += 1

    center_density = (center_black / center_total * 100) if center_total > 0 else 0

    return {
        "width": width,
        "height": height,
        "total_pixels": len(pixels),
        "black_pixels": black_pixels,
        "white_pixels": white_pixels,
        "black_percentage": black_percentage,
        "center_density": center_density,
        "bitmap_size_bytes": len(bitmap_data),
        "is_valid_qr": 25 <= black_percentage <= 65,  # Typical QR code density range
    }
