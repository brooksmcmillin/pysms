"""
Basic usage example for PySMS library.
"""

import time
from pysms import SMSHandler, SMS


def message_handler(sms: SMS):
    """Handle incoming SMS messages."""
    print("\nReceived SMS:")
    print(f"  From: {sms.sender}")
    print(f"  Date: {sms.date}")
    print(f"  Message: {sms.message}")
    print()


def main():
    # Initialize SMS handler
    # Replace with your actual serial port and baud rate
    port_name = "/dev/ttyUSB2"
    baud_rate = 115200

    try:
        sms_handler = SMSHandler(port_name, baud_rate)
        print("SMS handler initialized successfully!")

        # Example 1: Get modem information
        print("\n=== Modem Info ===")
        modem_info = sms_handler.get_modem_info()
        print(f"Modem: {modem_info}")

        signal_strength = sms_handler.get_signal_strength()
        print(f"Signal: {signal_strength}")

        # Example 2: Send an SMS
        phone_number = "+1234567890"  # Replace with actual phone number
        message = "Hello from PySMS library!"

        print("\n=== Sending SMS ===")
        print(f"Sending to {phone_number}...")
        sms_handler.send_sms(phone_number, message)
        print("SMS sent successfully!")

        # Example 3: Read existing SMS messages
        print("\n=== Reading SMS Messages ===")
        messages = sms_handler.read_sms()
        print(f"Found {len(messages)} messages:")

        for sms in messages:
            print(f"[{sms.index}] From {sms.sender}: {sms.message[:50]}...")

        # Example 4: Listen for incoming SMS messages
        print("\n=== Listening for Incoming SMS ===")
        print("Listening for incoming messages (press Ctrl+C to stop)...")

        sms_handler.listen_for_incoming_sms(message_handler)

        # Keep program running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Always close the connection
        if "sms_handler" in locals():
            sms_handler.close()
            print("SMS handler closed.")


if __name__ == "__main__":
    main()
