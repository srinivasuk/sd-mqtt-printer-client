#!/usr/bin/env python3
"""
Test script to monitor MQTT heartbeat messages.
This will subscribe to the heartbeat topic and log all messages received.
"""

import json
import time
import threading
import paho.mqtt.client as mqtt
from datetime import datetime

# Configuration
MQTT_BROKER = "printer.scandeer.com"
MQTT_PORT = 1883
MQTT_USERNAME = "vimal2"
MQTT_PASSWORD = "pa55word"
PRINTER_ID = "EE363AC5CF98"

# Topic to monitor
HEARTBEAT_TOPIC = f"{MQTT_USERNAME}/pt/{PRINTER_ID}/h"

print(f"🔍 MQTT Heartbeat Monitor")
print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"🔑 Username: {MQTT_USERNAME}")
print(f"📱 Printer ID: {PRINTER_ID}")
print(f"💓 Heartbeat Topic: {HEARTBEAT_TOPIC}")
print("=" * 60)

def on_connect(client, userdata, flags, rc):
    """Handle MQTT connection."""
    if rc == 0:
        print(f"✅ Connected to MQTT broker (code: {rc})")
        client.subscribe(HEARTBEAT_TOPIC, qos=0)
        print(f"📡 Subscribed to: {HEARTBEAT_TOPIC}")
    else:
        print(f"❌ Connection failed (code: {rc})")

def on_disconnect(client, userdata, rc):
    """Handle MQTT disconnection."""
    if rc != 0:
        print(f"⚠️ Unexpected disconnection (code: {rc})")
    else:
        print("🔌 Disconnected gracefully")

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"💓 [{timestamp}] Heartbeat received on: {topic}")
        
        # Try to parse JSON payload
        try:
            data = json.loads(payload)
            print(f"   📊 Data: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError:
            print(f"   📝 Raw payload: {payload}")
        
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Message handling error: {str(e)}")

def main():
    """Main function."""
    try:
        # Create MQTT client
        client = mqtt.Client(client_id=f"HeartbeatMonitor-{int(time.time())}")
        
        # Set credentials
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start network loop
        client.loop_start()
        
        print("🚀 Starting heartbeat monitor...")
        print("Press Ctrl+C to stop")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping heartbeat monitor...")
        client.loop_stop()
        client.disconnect()
        print("✅ Monitor stopped")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 