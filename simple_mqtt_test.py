#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import os
from dotenv import load_dotenv

load_dotenv()

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        print("✅ Connection successful!")
    else:
        print(f"❌ Connection failed: {rc}")

def on_disconnect(client, userdata, rc):
    print(f"Disconnected with result code {rc}")

# Create client
client = mqtt.Client(client_id="SimpleTest123")
client.username_pw_set(os.getenv("MQTT_USERNAME", "vimal2"), os.getenv("MQTT_PASSWORD", "pa55word"))
client.on_connect = on_connect
client.on_disconnect = on_disconnect

print("Connecting to MQTT broker...")
try:
    client.connect("printer.scandeer.com", 1883, 60)
    client.loop_start()
    
    print("Waiting 10 seconds...")
    time.sleep(10)
    
    client.loop_stop()
    client.disconnect()
    print("Test completed")
except Exception as e:
    print(f"Error: {e}")
