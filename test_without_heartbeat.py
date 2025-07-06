#!/usr/bin/env python3
"""
Test script without heartbeat to isolate MQTT issues.
"""

import os
import sys

# Reduce heartbeat frequency to test stability
os.environ['HEARTBEAT_INTERVAL'] = '300'  # 5 minutes (max allowed)
os.environ['PRINTER_NAME'] = 'gobbler_80mm_Series'

# Import and run the main application
sys.path.insert(0, 'src')
from src.main import main

if __name__ == "__main__":
    print("🔧 Running without heartbeat to test MQTT stability...")
    print(f"🖨️ Printer: {os.environ['PRINTER_NAME']}")
    print(f"💓 Heartbeat interval: {os.environ['HEARTBEAT_INTERVAL']}s")
    print("=" * 60)
    main() 