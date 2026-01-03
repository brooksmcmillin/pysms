#!/usr/bin/env python3
"""
Debug script to test SMS CLI functionality.
Run this to test the CLI with debug output enabled.
"""

import sys
import time
from pysms import SMSHandler


def test_sms_handler():
    """Test SMS handler basic functionality."""
    print("=== Testing SMS Handler ===")

    # Test with a dummy port (will fail but we can see the debug output)
    try:
        # Replace with your actual port
        port = "/dev/ttyUSB2"  # Change this to your actual port
        handler = SMSHandler(port, 115200, debug=True)

        print(f"✓ SMS Handler initialized on {port}")

        # Test callback function
        def message_callback(sms):
            print("📱 SMS Received!")
            print(f"   From: {sms.sender}")
            print(f"   Date: {sms.date}")
            print(f"   Message: {sms.message}")
            print(f"   Status: {sms.status}")
            print(f"   Index: {sms.index}")

        # Start listening
        print("🔍 Starting SMS listener...")
        handler.listen_for_incoming_sms(message_callback)

        print("📞 Listening for SMS messages (send a test message now)")
        print("Press Ctrl+C to stop...")

        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\\n🛑 Stopping...")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\\nTroubleshooting tips:")
        print("1. Check if your GSM modem is connected")
        print("2. Verify the serial port path (ls /dev/ttyUSB*)")
        print("3. Check permissions (sudo usermod -a -G dialout $USER)")
        print("4. Try a different baud rate")

    finally:
        if "handler" in locals():
            handler.close()
            print("✓ Handler closed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Debug script for PySMS CLI")
        print("\\nUsage: python debug_cli.py")
        print("\\nThis will:")
        print("- Test SMS handler initialization")
        print("- Enable debug output")
        print("- Listen for incoming SMS messages")
        print("- Show detailed debugging information")
        sys.exit(0)

    test_sms_handler()
