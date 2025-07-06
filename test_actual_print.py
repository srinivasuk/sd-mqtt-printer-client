 #!/usr/bin/env python3
"""
Test script to send realistic MQTT print orders with formatting and QR codes.
This simulates what the ESP32 firmware receives from the server.
"""

import json
import time
import paho.mqtt.client as mqtt
from typing import Dict, Any

# MQTT Configuration
MQTT_BROKER = "printer.scandeer.com"
MQTT_PORT = 1883
MQTT_USER = "vimal2"
MQTT_PASSWORD = "pa55word"

# Test printer MAC (replace with your Mac client's MAC)
PRINTER_MAC = "EE363AC5CF98"  # Example MAC
TOPIC_PRINT = f"{MQTT_USER}/pt/{PRINTER_MAC}/p"

def create_realistic_receipt() -> list:
    """
    Create a realistic receipt JSON array like the server sends.
    This matches the format that ESP32 firmware processes.
    """
    return [
        # Page metadata (like ESP32 firmware expects)
        {"page": 1, "of": 1},
        
        # Order metadata with order ID
        {"m": {"order_id": "TEST-460267"}},
        
        # Header formatting and text
        {"f": {"a": "c", "b": True, "s": 2}},  # Center, bold, large
        "Mythri Cinemas",
        
        {"f": {"a": "c", "b": False, "s": 1}},  # Center, normal, normal size
        "Balanagar Main Road",
        "Hyderabad, Telangana 500042",
        "",
        
        # Receipt details with left alignment
        {"f": {"a": "l", "b": False, "s": 1}},  # Left, normal, normal size
        "Order ID: TEST-460267",
        "Date: 2024-01-15 14:30:00",
        "Customer: Test Customer",
        "",
        
        # Items section with formatting
        {"f": {"a": "l", "b": True, "s": 1}},  # Left, bold, normal
        "ITEMS:",
        
        {"f": {"a": "l", "b": False, "s": 1}},  # Left, normal, normal
        "Movie: Test Movie",
        "Show: 2:30 PM",
        "Seats: A1, A2",
        "Price: Rs. 200.00",
        "",
        
        # Total with formatting
        {"f": {"a": "r", "b": True, "s": 1}},  # Right, bold, normal
        "TOTAL: Rs. 200.00",
        "",
        
        # QR Code section
        {"f": {"a": "c", "b": False, "s": 1}},  # Center, normal, normal
        "Scan QR for details:",
        "",
        
        # QR Code object (like ESP32 firmware expects)
        {
            "qr_bitmap": True,  # Indicates QR bitmap presence
            "qr_size": 12,      # QR size
            "qr_alignment": "center"  # QR alignment
        },
        
        "",
        
        # Footer
        {"f": {"a": "c", "b": False, "s": 0}},  # Center, normal, small
        "Thank you for visiting!",
        "Visit: scandeer.com",
        "",
        
        # Reset formatting
        {"f": {"a": "l", "b": False, "s": 1}}  # Left, normal, normal
    ]

def create_complex_receipt() -> list:
    """
    Create a complex receipt with multiple formatting changes.
    """
    return [
        # Page metadata
        {"page": 1, "of": 2},
        
        # Order metadata
        {"m": {"order_id": "COMPLEX-789"}},
        
        # Multiple formatting changes
        {"f": {"a": "c", "b": True, "s": 2}},
        "COMPLEX RECEIPT TEST",
        
        {"f": {"a": "l", "b": False, "s": 1}},
        "Testing multiple format changes:",
        "",
        
        {"f": {"a": "l", "b": True, "s": 1}},
        "Bold left text",
        
        {"f": {"a": "c", "b": True, "s": 1}},
        "Bold center text",
        
        {"f": {"a": "r", "b": True, "s": 1}},
        "Bold right text",
        
        {"f": {"a": "l", "b": False, "s": 1}},
        "Normal left text",
        
        {"f": {"a": "c", "b": False, "s": 1}},
        "Normal center text",
        
        {"f": {"a": "r", "b": False, "s": 1}},
        "Normal right text",
        
        {"f": {"a": "c", "b": False, "s": 2}},
        "Large center text",
        
        {"f": {"a": "c", "b": False, "s": 0}},
        "Small center text",
        
        # QR Code
        {"f": {"a": "c", "b": False, "s": 1}},
        "",
        "QR Code Test:",
        
        {
            "qr_url": "https://scandeer.com/order/COMPLEX-789",
            "qr_size": 10,
            "qr_alignment": "center"
        },
        
        {"f": {"a": "l", "b": False, "s": 1}},
        "",
        "End of complex test"
    ]

def on_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        print(f"✅ Connected to MQTT broker")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_publish(client, userdata, mid):
    """MQTT publish callback."""
    print(f"📤 Message published: {mid}")

def send_print_order(client: mqtt.Client, receipt_data: list, order_name: str):
    """Send a print order to the Mac client."""
    print(f"\n🖨️ Sending {order_name} to {TOPIC_PRINT}")
    
    # Convert to JSON like the server does
    json_payload = json.dumps(receipt_data, separators=(',', ':'))
    
    print(f"📄 Payload size: {len(json_payload)} bytes")
    print(f"📄 Elements: {len(receipt_data)}")
    
    # Publish the message
    result = client.publish(TOPIC_PRINT, json_payload, qos=0)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"✅ {order_name} sent successfully")
    else:
        print(f"❌ Failed to send {order_name}: {result.rc}")
    
    return result.rc == mqtt.MQTT_ERR_SUCCESS

def main():
    """Main test function."""
    print("🧪 MQTT Print Order Test")
    print("=" * 50)
    
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        # Connect to broker
        print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Test 1: Realistic receipt
        print("\n" + "="*50)
        print("TEST 1: Realistic Receipt with QR Code")
        print("="*50)
        
        realistic_receipt = create_realistic_receipt()
        success1 = send_print_order(client, realistic_receipt, "Realistic Receipt")
        
        if success1:
            print("⏱️ Waiting 10 seconds before next test...")
            time.sleep(10)
        
        # Test 2: Complex formatting
        print("\n" + "="*50)
        print("TEST 2: Complex Formatting Test")
        print("="*50)
        
        complex_receipt = create_complex_receipt()
        success2 = send_print_order(client, complex_receipt, "Complex Receipt")
        
        if success2:
            print("⏱️ Waiting 5 seconds...")
            time.sleep(5)
        
        # Test 3: Simple formatting test
        print("\n" + "="*50)
        print("TEST 3: Simple Format Test")
        print("="*50)
        
        simple_test = [
            {"page": 1, "of": 1},
            {"m": {"order_id": "SIMPLE-123"}},
            {"f": {"a": "c", "b": True, "s": 2}},
            "SIMPLE TEST",
            {"f": {"a": "l", "b": False, "s": 1}},
            "This should be left aligned",
            {"f": {"a": "c", "b": False, "s": 1}},
            "This should be center aligned",
            {"f": {"a": "r", "b": False, "s": 1}},
            "This should be right aligned",
            {"f": {"a": "l", "b": True, "s": 1}},
            "This should be bold",
            {"f": {"a": "l", "b": False, "s": 1}},
            "This should be normal"
        ]
        
        success3 = send_print_order(client, simple_test, "Simple Test")
        
        # Summary
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"Realistic Receipt: {'✅ SENT' if success1 else '❌ FAILED'}")
        print(f"Complex Receipt:   {'✅ SENT' if success2 else '❌ FAILED'}")
        print(f"Simple Test:       {'✅ SENT' if success3 else '❌ FAILED'}")
        print("\n📋 Check your Mac printer client logs to see if formatting works correctly!")
        print("📋 The receipts should show proper alignment, bold text, and size changes.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.loop_stop()
        client.disconnect()
        print("\n🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    main()