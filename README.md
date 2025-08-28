# PySMS

A Python library for handling SMS messages through serial port communication with GSM modems.

## Installation

```bash
pip install pysms
```

## Library Usage

```python
from pysms import SMSHandler, SMS

# Initialize the SMS handler
sms_handler = SMSHandler("/dev/ttyUSB2", 115200)

# Send an SMS
sms_handler.send_sms("+1234567890", "Hello, World!")

# Listen for incoming messages
def handle_sms(sms: SMS):
    print(f"Received SMS from {sms.sender}: {sms.message}")

sms_handler.listen_for_incoming_sms(handle_sms)

# Don't forget to close the connection
sms_handler.close()
```

## CLI Tool

The package includes a command-line chat interface for testing and recreational use.

### Usage

```bash
pysms-cli [OPTIONS] PHONE_NUMBER
```

**Options:**
- `--port`, `-p`: Serial port for GSM modem (default: /dev/ttyUSB2)
- `--baud`, `-b`: Serial port baud rate (default: 115200)
- `--debug`, `-d`: Enable debug output
- `--help`: Show help message

**Examples:**
```bash
# Basic usage
pysms-cli +1234567890

# Custom port and baud rate
pysms-cli +1234567890 --port /dev/ttyUSB0 --baud 9600

# Enable debug mode
pysms-cli +1234567890 --debug

# Short form options
pysms-cli +1234567890 -p /dev/ttyUSB0 -b 9600 -d

# View help
pysms-cli --help
```

### CLI Features

- Real-time chat interface
- Send and receive SMS messages  
- Multi-line message support (type `/multi`)
- Graceful shutdown with Ctrl+C
- Commands:
  - `/quit` or `/exit` - Exit the program
  - `/multi` - Enter multi-line mode (end with `.` on its own line)

## API Reference

### SMSHandler

The main class for SMS operations.

#### Constructor

```python
SMSHandler(port_name: str, baud_rate: int = 115200)
```

- `port_name`: Serial port name (e.g., '/dev/ttyUSB2', 'COM3')
- `baud_rate`: Serial communication baud rate (default: 115200)

#### Methods

**send_sms(phone_number: str, message: str) -> None**
- Send an SMS message

**read_sms() -> List[SMS]**
- Read all SMS messages

**read_new_sms() -> List[SMS]** 
- Read only unread SMS messages

**delete_sms(index: int) -> None**
- Delete an SMS message by index

**listen_for_incoming_sms(callback: Callable[[SMS], None]) -> None**
- Listen for incoming SMS notifications

**get_modem_info() -> str**
- Get modem information

**get_signal_strength() -> str**
- Get signal strength information

**close() -> None**
- Close the serial connection

### SMS

Data class representing an SMS message.

#### Attributes

- `index`: Message index (int)
- `status`: Message status (str)
- `sender`: Sender phone number (str) 
- `date`: Message date/time (str)
- `message`: Message text (str)

## Examples

See the `examples/` directory for more usage examples.

## Requirements

- Python 3.8 or later
- A GSM modem connected via serial port
- Appropriate permissions to access the serial port
- pyserial library

## Configuration

The default configuration uses:
- Port: `/dev/ttyUSB2` 
- Baud Rate: `115200`

You can modify these values when creating a new SMS handler instance.

## Development

To install for development:

```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black pysms/
```

Lint code:
```bash
flake8 pysms/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.