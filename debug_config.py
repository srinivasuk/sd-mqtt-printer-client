#!/usr/bin/env python3
"""
Debug script to check what configuration is being loaded.
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

print("🔧 Configuration Debug")
print("=" * 40)
print(f"MQTT_BROKER: {os.getenv('MQTT_BROKER', 'NOT SET')}")
print(f"MQTT_PORT: {os.getenv('MQTT_PORT', 'NOT SET')}")
print(f"MQTT_USERNAME: {os.getenv('MQTT_USERNAME', 'NOT SET')}")
print(f"MQTT_PASSWORD: {'***SET***' if os.getenv('MQTT_PASSWORD') else 'NOT SET'}")
print("=" * 40)

# Import config
try:
    from src.config import config
    print("✅ Config imported successfully")
    print(f"Config MQTT_USERNAME: {config.MQTT_USERNAME}")
    print(f"Config MQTT_BROKER: {config.MQTT_BROKER}")
    print(f"Config MQTT_PORT: {config.MQTT_PORT}")
    print(f"Config CLIENT_ID: {config.CLIENT_ID}")
    print(f"Config PRINTER_ID: {config.PRINTER_ID}")
except Exception as e:
    print(f"❌ Error importing config: {e}") 