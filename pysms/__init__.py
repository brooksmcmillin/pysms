"""
PySMS - A Python library for handling SMS messages through serial communication with GSM modems.

This library provides a simple interface for sending and receiving SMS messages
using AT commands over serial connections to GSM modems.
"""

from .sms_handler import SMSHandler, SMS

__version__ = "0.1.0"
__all__ = ["SMSHandler", "SMS"]