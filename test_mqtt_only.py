#!/usr/bin/env python3
"""
Minimal MQTT test - connect and subscribe only, no publishing.
"""

import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "printer.scandeer.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "vimal2")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "pa55word")
CLIENT_ID = "TestClient-Minimal-12345"

print("🔧 Minimal MQTT Test - Subscribe Only")
print("=" * 50)
print(f"🌐 Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"👤 Username: {MQTT_USERNAME}")
print(f"🆔 Client ID: {CLIENT_ID}")
print("=" * 50)

connected = False
disconnected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("✅ Connected successfully!")
        connected = True
        # Only subscribe, don't publish anything
        client.subscribe("vimal2/pt/EE363AC5CF98/p", qos=1)
        print("📡 Subscribed to print topic")
    else:
        print(f"❌ Connection failed: {rc}")

def on_disconnect(client, userdata, rc):
    global disconnected
    disconnected = True
    if rc != 0:
        print(f"⚠️ Unexpected disconnection: {rc}")
    else:
        print("🔌 Disconnected gracefully")

def on_message(client, userdata, msg):
    print(f"📨 Message received on {msg.topic}: {len(msg.payload)} bytes")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"✅ Subscription confirmed with QoS: {granted_qos}")

# Create client
client = mqtt.Client(client_id=CLIENT_ID)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_subscribe = on_subscribe

try:
    print("🔄 Connecting...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    
    # Wait and monitor connection
    start_time = time.time()
    while time.time() - start_time < 30:  # Monitor for 30 seconds
        if disconnected:
            print("❌ Connection lost")
            break
        if connected:
            elapsed = int(time.time() - start_time)
            print(f"⏱️  Connected for {elapsed}s", end='\r')
        time.sleep(1)
    
    print("\n🔧 Test completed")
    client.loop_stop()
    client.disconnect()
    
except Exception as e:
    print(f"❌ Error: {e}") 