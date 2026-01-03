"""
SMS Handler module for communicating with GSM modems via serial port.
"""

import re
import time
import threading
from dataclasses import dataclass
from typing import Callable
import serial


@dataclass
class SMS:
    """Represents an SMS message."""

    index: int = 0
    status: str = ""
    sender: str = ""
    date: str = ""
    message: str = ""


class SMSHandler:
    """Handles SMS operations through serial communication with GSM modems."""

    def __init__(self, port_name: str, baud_rate: int = 115200, debug: bool = False):
        """
        Initialize SMS handler.

        Args:
            port_name: Serial port name (e.g., '/dev/ttyUSB2', 'COM3')
            baud_rate: Serial communication baud rate
            debug: Enable debug output
        """
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.debug = debug
        self.serial_conn: serial.Serial | None = None
        self.listening = False
        self._listen_thread: threading.Thread | None = None
        self._pause_event = threading.Event()
        self._resume_event = threading.Event()
        self._lock = threading.Lock()

        # Initialize connection
        self._connect()
        self._init_modem()

    @property
    def _serial(self) -> serial.Serial:
        """Get the serial connection, raising if not connected."""
        if self.serial_conn is None:
            raise RuntimeError("Serial connection not established")
        return self.serial_conn

    def _connect(self):
        """Establish serial connection."""
        try:
            self.serial_conn = serial.Serial(
                port=self.port_name,
                baudrate=self.baud_rate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1.0,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to open serial port: {e}")

    def _init_modem(self):
        """Initialize the modem with basic AT commands."""
        init_commands = [
            ("AT", "Test AT communication"),
            ("AT+CMGF=1", "Set SMS text mode"),
            ('AT+CSCS="GSM"', "Set character set to GSM"),
            ('AT+CPMS="SM","SM","SM"', "Set SMS storage location"),
        ]

        for cmd, desc in init_commands:
            response = self._send_at_command(cmd)
            if "OK" not in response:
                raise RuntimeError(f"Failed to {desc}: {response}")

        # Try different SMS notification settings for compatibility
        notification_commands = [
            "AT+CNMI=1,2,0,1,0",
            "AT+CNMI=2,1,0,2,0",
            "AT+CNMI=1,1,0,1,0",
        ]

        success = False
        for cmd in notification_commands:
            try:
                response = self._send_at_command(cmd)
                if "OK" in response:
                    success = True
                    break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] Notification command {cmd} failed: {e}")
                # Try the next notification command

        if not success:
            raise RuntimeError("Failed to enable SMS notifications")

    def _send_at_command(self, command: str, timeout: float = 10.0) -> str:
        """
        Send AT command and wait for response.

        Args:
            command: AT command to send
            timeout: Command timeout in seconds

        Returns:
            Response from modem
        """
        with self._lock:
            self._pause_listener()

            try:
                # Clear input buffer
                self._serial.reset_input_buffer()

                # Send command
                cmd_bytes = (command + "\r\n").encode()
                self._serial.write(cmd_bytes)

                # Read response
                response = ""
                start_time = time.time()
                consecutive_empty = 0

                while time.time() - start_time < timeout:
                    if self._serial.in_waiting:
                        line = (
                            self._serial.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )

                        # Skip echo of command
                        if line == command:
                            continue

                        # Handle empty lines
                        if not line:
                            consecutive_empty += 1
                            if consecutive_empty > 3:
                                break
                            continue

                        consecutive_empty = 0
                        response += line + "\n"

                        # Check for terminal responses
                        if any(term in line for term in ["OK", "ERROR", "+CME ERROR"]):
                            break
                    else:
                        time.sleep(0.1)

                return response.strip()

            finally:
                self._resume_listener()

    def _pause_listener(self):
        """Pause the SMS listener temporarily."""
        if self.listening and self._listen_thread and self._listen_thread.is_alive():
            self._pause_event.set()
            # Wait for listener to acknowledge pause
            self._resume_event.wait(timeout=1.0)
            self._resume_event.clear()

    def _resume_listener(self):
        """Resume the SMS listener."""
        if self.listening and self._pause_event.is_set():
            self._pause_event.clear()
            self._resume_event.set()

    def close(self):
        """Close the serial connection."""
        self.listening = False
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=2.0)

        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def get_modem_info(self) -> str:
        """Get modem information."""
        return self._send_at_command("ATI")

    def get_signal_strength(self) -> str:
        """Get signal strength information."""
        return self._send_at_command("AT+CSQ")

    def send_sms(self, phone_number: str, message: str) -> None:
        """
        Send an SMS message.

        Args:
            phone_number: Recipient phone number
            message: Message text to send
        """
        with self._lock:
            self._pause_listener()

            try:
                # Clear buffers
                self._serial.reset_input_buffer()
                time.sleep(0.1)

                # Start SMS composition
                cmd = f'AT+CMGS="{phone_number}"'
                self._serial.write((cmd + "\r").encode())

                # Wait for prompt
                prompt_received = False
                start_time = time.time()

                while time.time() - start_time < 10.0:
                    if self._serial.in_waiting:
                        data = self._serial.read(self._serial.in_waiting).decode(
                            "utf-8", errors="ignore"
                        )
                        if ">" in data:
                            prompt_received = True
                            break
                    time.sleep(0.1)

                if not prompt_received:
                    raise RuntimeError("Timeout waiting for SMS prompt")

                time.sleep(0.1)

                # Send message with Ctrl+Z terminator
                full_message = message + "\x1a"
                self._serial.write(full_message.encode())

                # Wait for response
                response = ""
                start_time = time.time()

                while time.time() - start_time < 30.0:
                    if self._serial.in_waiting:
                        data = self._serial.read(self._serial.in_waiting).decode(
                            "utf-8", errors="ignore"
                        )
                        response += data

                        if "+CMGS:" in response or "OK" in response:
                            return
                        if "ERROR" in response or "+CMS ERROR" in response:
                            raise RuntimeError(f"SMS failed: {response}")

                    time.sleep(0.1)

                raise RuntimeError("SMS timeout - no valid response received")

            finally:
                self._resume_listener()

    def read_sms(self) -> list[SMS]:
        """Read all SMS messages."""
        response = self._send_at_command('AT+CMGL="ALL"')
        return self._parse_sms_list(response)

    def read_new_sms(self) -> list[SMS]:
        """Read only unread SMS messages."""
        response = self._send_at_command('AT+CMGL="REC UNREAD"')
        return self._parse_sms_list(response)

    def _parse_sms_list(self, response: str) -> list[SMS]:
        """Parse SMS list response."""
        messages = []
        lines = response.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("+CMGL:"):
                # Parse header: +CMGL: index,status,sender,date
                match = re.search(
                    r'\+CMGL:\s*(\d+),\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"', line
                )
                if match:
                    sms = SMS(
                        index=int(match.group(1)),
                        status=match.group(2),
                        sender=match.group(3),
                        date=match.group(4),
                    )

                    # Next line should contain the message
                    if i + 1 < len(lines):
                        sms.message = lines[i + 1].strip()
                        i += 1

                    messages.append(sms)
            i += 1

        return messages

    def delete_sms(self, index: int) -> None:
        """Delete an SMS message by index."""
        cmd = f"AT+CMGD={index}"
        response = self._send_at_command(cmd)
        if "OK" not in response:
            raise RuntimeError(f"Failed to delete SMS: {response}")

    def listen_for_incoming_sms(self, callback: Callable[[SMS], None]) -> None:
        """
        Listen for incoming SMS notifications.

        Args:
            callback: Function to call when SMS is received
        """
        self.listening = True
        self._listen_thread = threading.Thread(
            target=self._sms_listener, args=(callback,), daemon=True
        )
        self._listen_thread.start()

    def _sms_listener(self, callback: Callable[[SMS], None]) -> None:
        """SMS listener thread function."""
        if self.debug:
            print("[DEBUG] SMS listener started")
        try:
            while self.listening:
                # Check for pause
                if self._pause_event.is_set():
                    # Acknowledge pause
                    self._resume_event.set()
                    # Wait for resume signal
                    while self._pause_event.is_set() and self.listening:
                        time.sleep(0.1)
                    continue

                if not self._serial.in_waiting:
                    time.sleep(0.1)
                    continue

                try:
                    line = (
                        self._serial.readline().decode("utf-8", errors="ignore").strip()
                    )
                    if not line:
                        continue

                    if self.debug:
                        print(f"[DEBUG] Raw line received: {repr(line)}")

                    # Filter out AT responses
                    if self._is_at_response(line):
                        if self.debug:
                            print(f"[DEBUG] Filtered AT response: {line}")
                        continue

                    if self.debug:
                        print(f"[DEBUG] Processing line: {line}")

                    # Handle direct SMS delivery: +CMT:
                    if line.startswith("+CMT:"):
                        if self.debug:
                            print(f"[DEBUG] Handling CMT message: {line}")
                        self._handle_cmt_message(line, callback)

                    # Handle stored message notifications: +CMTI:
                    elif line.startswith("+CMTI:"):
                        if self.debug:
                            print(f"[DEBUG] Handling CMTI message: {line}")
                        self._handle_cmti_message(line, callback)
                    else:
                        if self.debug:
                            print(f"[DEBUG] Unhandled line: {line}")

                except Exception as e:
                    print(f"[ERROR] Error in SMS listener: {e}")
                    import traceback

                    traceback.print_exc()
                    continue

        except Exception as e:
            print(f"[ERROR] SMS listener crashed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if self.debug:
                print("[DEBUG] SMS listener stopped")

    def _is_at_response(self, line: str) -> bool:
        """Check if line is an AT command response to filter out."""
        if line.startswith("AT") or line in ["OK", "ERROR"]:
            return True

        # Filter specific responses
        response_prefixes = ["+CMGF:", "+CSCS:", "+CPMS:", "+CNMI:", "+CSQ:"]
        return any(line.startswith(prefix) for prefix in response_prefixes)

    def _handle_cmt_message(self, line: str, callback: Callable[[SMS], None]) -> None:
        """Handle direct SMS delivery notifications (+CMT)."""
        if self.debug:
            print(f"[DEBUG] Parsing CMT header: {line}")

        # Parse CMT header: +CMT: "+11234567890","","25/07/21,21:07:17-28"
        match = re.search(r'\+CMT:\s*"([^"]*)",\s*"[^"]*",\s*"([^"]*)"', line)
        if not match:
            if self.debug:
                print(f"[DEBUG] Failed to parse CMT header: {line}")
            return

        sms = SMS(sender=match.group(1), date=match.group(2))

        if self.debug:
            print(f"[DEBUG] Parsed sender: {sms.sender}, date: {sms.date}")

        # Read message content that follows
        message_lines = []
        start_time = time.time()

        if self.debug:
            print("[DEBUG] Reading message content...")
        while time.time() - start_time < 2.0:
            if self._serial.in_waiting:
                try:
                    msg_line = (
                        self._serial.readline().decode("utf-8", errors="ignore").strip()
                    )
                    if self.debug:
                        print(f"[DEBUG] Message line: {repr(msg_line)}")

                    # Skip empty lines at beginning
                    if not msg_line and not message_lines:
                        continue

                    # Check if this is end of message or next notification
                    if msg_line.startswith(
                        ("+CMT:", "+CMTI:", "OK", "ERROR", "AT+")
                    ) or (not msg_line and message_lines):
                        if self.debug:
                            print("[DEBUG] End of message detected")
                        break

                    if msg_line:
                        message_lines.append(msg_line)

                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] Error reading message line: {e}")
                    break
            else:
                time.sleep(0.05)

        if message_lines:
            sms.message = "\n".join(message_lines)
            if self.debug:
                print(f"[DEBUG] Complete SMS: from={sms.sender}, message={sms.message}")
            callback(sms)
        else:
            if self.debug:
                print("[DEBUG] No message content found for CMT")

    def _handle_cmti_message(self, line: str, callback: Callable[[SMS], None]) -> None:
        """Handle stored message notifications (+CMTI)."""
        if self.debug:
            print(f"[DEBUG] Parsing CMTI: {line}")

        # Parse CMTI: +CMTI: "SM",index
        match = re.search(r'\+CMTI:\s*"[^"]*",\s*(\d+)', line)
        if not match:
            if self.debug:
                print(f"[DEBUG] Failed to parse CMTI: {line}")
            return

        index = int(match.group(1))
        if self.debug:
            print(f"[DEBUG] Reading SMS at index {index}")

        try:
            sms = self._read_sms_by_index(index)
            if self.debug:
                print(
                    f"[DEBUG] Retrieved SMS: from={sms.sender}, message={sms.message}"
                )
            callback(sms)
        except Exception as e:
            print(f"[ERROR] Error reading SMS by index {index}: {e}")
            import traceback

            traceback.print_exc()

    def _read_sms_by_index(self, index: int) -> SMS:
        """Read a specific SMS message by index."""
        cmd = f"AT+CMGR={index}"
        response = self._send_at_command(cmd)

        lines = response.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("+CMGR:"):
                # Parse header: +CMGR: status,sender,date
                match = re.search(
                    r'\+CMGR:\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"', line
                )
                if match:
                    sms = SMS(
                        index=index,
                        status=match.group(1),
                        sender=match.group(2),
                        date=match.group(3),
                    )

                    # Next line contains message
                    if i + 1 < len(lines):
                        sms.message = lines[i + 1].strip()

                    return sms

        raise RuntimeError("Failed to parse SMS")
