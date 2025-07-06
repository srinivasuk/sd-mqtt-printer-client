#!/usr/bin/env python3
"""
Temporary script to run the application with correct MQTT credentials.
"""

import os
import sys

# Set the correct MQTT credentials
os.environ['MQTT_USERNAME'] = 'sd_mqtt_user'
os.environ['MQTT_PASSWORD'] = 'mqttPa55w0rd890Na99u'

# Import and run the main application
sys.path.insert(0, 'src')
from src.main import main

if __name__ == "__main__":
    print("🔧 Running with correct MQTT credentials...")
    print(f"👤 Username: {os.environ['MQTT_USERNAME']}")
    print(f"🔑 Password: {'***SET***' if os.environ['MQTT_PASSWORD'] else 'NOT SET'}")
    print("=" * 60)
    main() 