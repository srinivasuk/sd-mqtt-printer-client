#!/usr/bin/env python3
"""
Simple MQTT connection test to verify credentials.
"""

import os
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "printer.scandeer.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "vimal1")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "pa55word")

print("🔧 MQTT Connection Test")
print("=" * 40)
print(f"🌐 Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"👤 Username: {MQTT_USERNAME}")
print(f"🔑 Password: {'***SET***' if MQTT_PASSWORD else 'NOT SET'}")
print("=" * 40)

# Connection result tracking
connection_result = None
connection_successful = False

def on_connect(client, userdata, flags, rc):
    global connection_result, connection_successful
    connection_result = rc
    
    if rc == 0:
        print("✅ Connected successfully!")
        connection_successful = True
    else:
        error_messages = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        print(f"❌ Connection failed: {error_messages.get(rc, f'Unknown error code {rc}')}")
        connection_successful = False

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️ Unexpected disconnection: {rc}")
    else:
        print("🔌 Disconnected gracefully")

# Create client
client = mqtt.Client(client_id="TestClient-12345")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

try:
    print("🔄 Connecting...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    
    # Wait for connection result
    timeout = 10
    start_time = time.time()
    
    while connection_result is None and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    if connection_result is None:
        print("❌ Connection timeout")
    elif connection_successful:
        print("✅ Connection test successful!")
        time.sleep(2)  # Keep connection alive briefly
    
    client.loop_stop()
    client.disconnect()
    
except Exception as e:
    print(f"❌ Connection error: {e}")

print("\n�� Test completed") 