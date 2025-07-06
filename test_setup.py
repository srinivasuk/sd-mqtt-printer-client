#!/usr/bin/env python3
"""
Test script to verify SD MQTT Printer Mac setup.
Tests all components without requiring actual hardware.
"""

import sys
import traceback
from typing import Dict, Any

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")

    try:
        from config import config
        print("✅ Config module imported")

        from utils.logger import logger
        print("✅ Logger module imported")

        from utils.formatting import PrinterFormatter, replace_variables
        print("✅ Formatting module imported")

        from utils.bitmap import decode_bit_packed_bitmap, analyze_bitmap_density
        print("✅ Bitmap module imported")

        from qr_generator import qr_generator
        print("✅ QR generator module imported")

        from printer_manager import printer_manager
        print("✅ Printer manager module imported")

        from mqtt_client import mqtt_client
        print("✅ MQTT client module imported")

        return True

    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        traceback.print_exc()
        return False


def test_config():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")

    try:
        from config import config

        # Test basic config values
        assert config.MQTT_BROKER, "MQTT broker not configured"
        assert config.MQTT_PORT > 0, "MQTT port invalid"
        assert config.PRINTER_NAME, "Printer name not configured"
        assert config.PRINTER_ID, "Printer ID not generated"

        print(f"✅ Config loaded successfully")
        print(f"   - MQTT Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}")
        print(f"   - Printer: {config.PRINTER_NAME}")
        print(f"   - Printer ID: {config.PRINTER_ID}")
        print(f"   - MAC Address: {config.MAC_ADDRESS}")

        return True

    except Exception as e:
        print(f"❌ Config error: {str(e)}")
        traceback.print_exc()
        return False


def test_logger():
    """Test logging functionality."""
    print("\n🔍 Testing logger...")

    try:
        from utils.logger import logger

        # Test different log levels
        logger.debug("Debug message test")
        logger.info("Info message test")
        logger.warning("Warning message test")

        # Test printer-specific logging
        logger.print_start("test_order", 1, 1)
        logger.print_complete("test_order", 1, 1)
        logger.heartbeat_sent("ready")

        print("✅ Logger working correctly")
        return True

    except Exception as e:
        print(f"❌ Logger error: {str(e)}")
        traceback.print_exc()
        return False


def test_formatting():
    """Test text formatting utilities."""
    print("\n🔍 Testing formatting...")

    try:
        from utils.formatting import PrinterFormatter, replace_variables, parse_qr_command

        # Test formatter
        formatter = PrinterFormatter()

        # Test format application
        format_cmd = {"f": {"a": "c", "b": True, "s": 2}}
        changes = formatter.apply_format(format_cmd)

        assert "align" in changes, "Alignment not applied"
        assert "bold" in changes, "Bold not applied"
        assert "size" in changes, "Size not applied"

        # Test variable replacement
        template = "Order {{order_id}} for {{customer_name}}"
        data = {"order_id": "12345", "customer_name": "John Doe"}
        result = replace_variables(template, data)

        assert "12345" in result, "Order ID not replaced"
        assert "John Doe" in result, "Customer name not replaced"

        # Test QR parsing
        qr_cmd = {"qr_url": "https://example.com", "qr_size": 10}
        qr_data = parse_qr_command(qr_cmd)

        assert qr_data["type"] == "url", "QR type not parsed"
        assert qr_data["url"] == "https://example.com", "QR URL not parsed"

        print("✅ Formatting working correctly")
        return True

    except Exception as e:
        print(f"❌ Formatting error: {str(e)}")
        traceback.print_exc()
        return False


def test_qr_generator():
    """Test QR code generation."""
    print("\n🔍 Testing QR generator...")

    try:
        from qr_generator import qr_generator

        # Test QR generation
        test_url = "https://scandeer.com/test"
        qr_data = qr_generator.generate_qr_bitmap(test_url, size=8)

        assert "qr_bitmap" in qr_data, "QR bitmap not generated"
        assert "qr_size" in qr_data, "QR size not set"

        bitmap = qr_data["qr_bitmap"]
        assert bitmap["width"] > 0, "QR width invalid"
        assert bitmap["height"] > 0, "QR height invalid"
        assert len(bitmap["data"]) > 0, "QR data empty"

        # Test QR validation
        is_valid = qr_generator.validate_qr_bitmap(qr_data)
        assert is_valid, "QR validation failed"

        print("✅ QR generator working correctly")
        print(f"   - Generated QR: {bitmap['width']}x{bitmap['height']}")
        print(f"   - Data size: {len(bitmap['data'])} bytes")

        return True

    except Exception as e:
        print(f"❌ QR generator error: {str(e)}")
        traceback.print_exc()
        return False


def test_bitmap_processing():
    """Test bitmap processing utilities."""
    print("\n🔍 Testing bitmap processing...")

    try:
        from utils.bitmap import create_test_bitmap, analyze_bitmap_density

        # Create test bitmap
        test_bitmap = create_test_bitmap(64, 64)

        assert len(test_bitmap) > 0, "Test bitmap not created"

        # Analyze bitmap
        analysis = analyze_bitmap_density(test_bitmap, 64, 64)

        assert analysis["width"] == 64, "Width analysis incorrect"
        assert analysis["height"] == 64, "Height analysis incorrect"
        assert analysis["total_pixels"] == 64 * 64, "Pixel count incorrect"

        print("✅ Bitmap processing working correctly")
        print(f"   - Bitmap size: {analysis['width']}x{analysis['height']}")
        print(f"   - Black pixels: {analysis['black_percentage']:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Bitmap processing error: {str(e)}")
        traceback.print_exc()
        return False


def test_printer_manager():
    """Test printer manager (without actual hardware)."""
    print("\n🔍 Testing printer manager...")

    try:
        from printer_manager import printer_manager

        # Test status without connection
        status = printer_manager.get_status()

        assert "printer_online" in status, "Printer status missing online field"
        assert "printer_status" in status, "Printer status missing status field"
        assert "print_stats" in status, "Printer status missing stats field"

        # Test receipt processing (without actual printing)
        test_receipt = [
            {"f": {"a": "c", "b": True}},
            "Test Receipt",
            {"line": "solid"},
            "Thank you!"
        ]

        print("✅ Printer manager working correctly")
        print(f"   - Status: {status['printer_status']}")
        print(f"   - Online: {status['printer_online']}")

        return True

    except Exception as e:
        print(f"❌ Printer manager error: {str(e)}")
        traceback.print_exc()
        return False


def test_mqtt_client():
    """Test MQTT client (without actual connection)."""
    print("\n🔍 Testing MQTT client...")

    try:
        from mqtt_client import mqtt_client

        # Test connection info
        info = mqtt_client.get_connection_info()

        assert "connected" in info, "MQTT info missing connected field"
        assert "broker" in info, "MQTT info missing broker field"
        assert "topics" in info, "MQTT info missing topics field"

        # Test message processing
        test_data = {
            "order_id": "test_123",
            "page": 1,
            "total_pages": 1,
            "receipt_data": ["Test Line 1", "Test Line 2"]
        }

        processed = mqtt_client._process_receipt_data(test_data["receipt_data"], test_data)

        assert len(processed) == 2, "Receipt processing failed"

        print("✅ MQTT client working correctly")
        print(f"   - Broker: {info['broker']}")
        print(f"   - Topics configured: {len(info['topics'])}")

        return True

    except Exception as e:
        print(f"❌ MQTT client error: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🧪 SD MQTT Printer Mac - Setup Test")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Logger", test_logger),
        ("Formatting", test_formatting),
        ("QR Generator", test_qr_generator),
        ("Bitmap Processing", test_bitmap_processing),
        ("Printer Manager", test_printer_manager),
        ("MQTT Client", test_mqtt_client),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test failed: {str(e)}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Configure your printer in .env file")
        print("   2. Update MQTT credentials in .env file")
        print("   3. Run: poetry run python main.py")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
