#!/usr/bin/env python3
"""
Debug script to analyze heartbeat messages and compare with ESP32 firmware format.
This script will help identify why Python client heartbeats aren't being received by the server.
"""

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "printer.scandeer.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "vimal1")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "pa55word")
PRINTER_ID = "AABBCCDDEEFF"  # Test printer ID

# Topics
HEARTBEAT_TOPIC = f"{MQTT_USERNAME}/pt/{PRINTER_ID}/h"
PRINT_TOPIC = f"{MQTT_USERNAME}/pt/{PRINTER_ID}/p"
STATUS_TOPIC = f"{MQTT_USERNAME}/pt/{PRINTER_ID}/a"
ERROR_TOPIC = f"{MQTT_USERNAME}/pt/{PRINTER_ID}/e"

print("🔍 MQTT Heartbeat Debug Tool")
print("=" * 50)
print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Username: {MQTT_USERNAME}")
print(f"Printer ID: {PRINTER_ID}")
print(f"Heartbeat Topic: {HEARTBEAT_TOPIC}")
print("=" * 50)

def create_esp32_style_heartbeat():
    """Create heartbeat message in ESP32 firmware format."""
    return {
        "printer_id": PRINTER_ID,
        "timestamp": int(time.time() * 1000),  # Milliseconds like ESP32
        "esp32_status": "online",
        "printer_online": True,
        "printer_status": "ready",
        "details": {
            "paper_present": True,
            "cover_closed": True,
            "cutter_ok": True,
            "wifi_connected": True,
            "mqtt_connected": True,
            "free_heap": 150000,
            "uptime_ms": int(time.time() * 1000),
            "wifi_rssi": -45,
            "local_ip": "192.168.1.100"
        }
    }

def create_python_client_heartbeat():
    """Create heartbeat message in Python client format."""
    return {
        "printer_id": PRINTER_ID,
        "timestamp": int(time.time() * 1000),
        "esp32_status": "online",
        "printer_online": True,
        "printer_status": "ready",
        "details": {
            "paper_present": True,
            "cover_closed": True,
            "cutter_ok": True,
            "wifi_connected": True,
            "mqtt_connected": True,
            "free_heap": 8192,
            "uptime_ms": int(time.time() * 1000),
            "wifi_rssi": -50,
            "local_ip": "192.168.1.200"
        }
    }

def on_connect(client, userdata, flags, rc):
    """Handle MQTT connection."""
    if rc == 0:
        print("✅ Connected to MQTT broker")
        
        # Subscribe to all topics to monitor traffic
        client.subscribe(f"{MQTT_USERNAME}/pt/{PRINTER_ID}/#")
        client.subscribe(f"+/pt/+/h")  # Monitor all heartbeats
        print("📡 Subscribed to debug topics")
        
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Handle incoming messages."""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"\n📨 Message received:")
        print(f"   Topic: {topic}")
        print(f"   Size: {len(payload)} bytes")
        
        # Try to parse as JSON
        try:
            data = json.loads(payload)
            print(f"   JSON: {json.dumps(data, indent=2)}")
        except:
            print(f"   Raw: {payload}")
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")

def send_test_heartbeat(client, heartbeat_type="esp32"):
    """Send test heartbeat message."""
    try:
        if heartbeat_type == "esp32":
            heartbeat = create_esp32_style_heartbeat()
            print("\n💓 Sending ESP32-style heartbeat...")
        else:
            heartbeat = create_python_client_heartbeat()
            print("\n💓 Sending Python client-style heartbeat...")
        
        payload = json.dumps(heartbeat)
        print(f"   Topic: {HEARTBEAT_TOPIC}")
        print(f"   Size: {len(payload)} bytes")
        print(f"   Payload: {payload}")
        
        result = client.publish(HEARTBEAT_TOPIC, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ Heartbeat sent successfully")
        else:
            print(f"❌ Heartbeat send failed: {result.rc}")
            
    except Exception as e:
        print(f"❌ Error sending heartbeat: {e}")

def main():
    """Main debug function."""
    print("\n🚀 Starting heartbeat debug session...")
    
    # Create MQTT client
    client = mqtt.Client(client_id=f"debug_client_{int(time.time())}")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Connect to broker
        print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Send test heartbeats
        print("\n" + "=" * 50)
        print("HEARTBEAT COMPARISON TEST")
        print("=" * 50)
        
        # Test 1: ESP32 style heartbeat
        send_test_heartbeat(client, "esp32")
        time.sleep(3)
        
        # Test 2: Python client style heartbeat
        send_test_heartbeat(client, "python")
        time.sleep(3)
        
        # Test 3: Monitor for responses
        print("\n👂 Monitoring for 10 seconds...")
        time.sleep(10)
        
        print("\n✅ Debug session completed")
        
    except Exception as e:
        print(f"❌ Debug session error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main() 