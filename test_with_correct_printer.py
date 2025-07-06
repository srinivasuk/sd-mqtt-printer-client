#!/usr/bin/env python3
"""
Test script with correct printer name.
"""

import os
import sys

# Set the correct printer name
os.environ['PRINTER_NAME'] = 'gobbler_80mm_Series'

# Import and run the main application
sys.path.insert(0, 'src')
from src.main import main

if __name__ == "__main__":
    print("🔧 Running with correct printer name...")
    print(f"🖨️ Printer: {os.environ['PRINTER_NAME']}")
    print("=" * 60)
    main() 