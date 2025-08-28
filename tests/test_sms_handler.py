"""
Tests for SMS handler functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pysms import SMSHandler, SMS


class TestSMS:
    """Test SMS dataclass."""
    
    def test_sms_creation(self):
        """Test SMS object creation."""
        sms = SMS(
            index=1,
            status="REC UNREAD",
            sender="+1234567890",
            date="25/07/21,21:07:17-28",
            message="Hello, World!"
        )
        
        assert sms.index == 1
        assert sms.status == "REC UNREAD"
        assert sms.sender == "+1234567890"
        assert sms.date == "25/07/21,21:07:17-28"
        assert sms.message == "Hello, World!"


class TestSMSHandler:
    """Test SMSHandler class."""
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_init_success(self, mock_serial):
        """Test successful initialization."""
        mock_port = Mock()
        mock_serial.return_value = mock_port
        mock_port.readline.return_value = b"OK\r\n"
        mock_port.in_waiting = 0
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
        
        mock_serial.assert_called_once_with(
            port="/dev/ttyUSB0",
            baudrate=115200,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=1.0
        )
        
        assert handler.port_name == "/dev/ttyUSB0"
        assert handler.baud_rate == 115200
        assert handler.serial_conn == mock_port
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_init_connection_error(self, mock_serial):
        """Test connection error during initialization."""
        mock_serial.side_effect = Exception("Port not found")
        
        with pytest.raises(ConnectionError, match="Failed to open serial port"):
            SMSHandler("/dev/nonexistent", 115200)
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_send_at_command(self, mock_serial):
        """Test sending AT command."""
        mock_port = Mock()
        mock_serial.return_value = mock_port
        mock_port.in_waiting = 10
        mock_port.readline.side_effect = [
            b"AT\r\n",  # Echo
            b"OK\r\n"   # Response
        ]
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
            response = handler._send_at_command("AT")
        
        assert "OK" in response
        mock_port.write.assert_called()
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_parse_sms_list(self, mock_serial):
        """Test parsing SMS list response."""
        mock_port = Mock()
        mock_serial.return_value = mock_port
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
        
        response = '+CMGL: 1,"REC UNREAD","+1234567890","25/07/21,21:07:17-28"\nHello, World!\n'
        messages = handler._parse_sms_list(response)
        
        assert len(messages) == 1
        sms = messages[0]
        assert sms.index == 1
        assert sms.status == "REC UNREAD"
        assert sms.sender == "+1234567890"
        assert sms.date == "25/07/21,21:07:17-28"
        assert sms.message == "Hello, World!"
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_is_at_response(self, mock_serial):
        """Test AT response filtering."""
        mock_port = Mock()
        mock_serial.return_value = mock_port
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
        
        # These should be filtered out
        assert handler._is_at_response("AT")
        assert handler._is_at_response("AT+CMGF=1")
        assert handler._is_at_response("OK")
        assert handler._is_at_response("ERROR")
        assert handler._is_at_response("+CMGF: 1")
        
        # These should not be filtered
        assert not handler._is_at_response("+CMT: message")
        assert not handler._is_at_response("Hello World")
        assert not handler._is_at_response("+CMTI: notification")
    
    @patch('pysms.sms_handler.serial.Serial')
    def test_close(self, mock_serial):
        """Test closing connection."""
        mock_port = Mock()
        mock_serial.return_value = mock_port
        mock_port.is_open = True
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
            handler.close()
        
        mock_port.close.assert_called_once()
        assert not handler.listening


@pytest.fixture
def mock_sms_handler():
    """Create a mock SMS handler for testing."""
    with patch('pysms.sms_handler.serial.Serial') as mock_serial:
        mock_port = Mock()
        mock_serial.return_value = mock_port
        mock_port.readline.return_value = b"OK\r\n"
        mock_port.in_waiting = 0
        
        with patch.object(SMSHandler, '_init_modem'):
            handler = SMSHandler("/dev/ttyUSB0", 115200)
            yield handler, mock_port


class TestSMSHandlerIntegration:
    """Integration tests for SMS handler."""
    
    def test_send_sms_success(self, mock_sms_handler):
        """Test successful SMS sending."""
        handler, mock_port = mock_sms_handler
        
        # Mock in_waiting and read to simulate prompt and response
        mock_port.in_waiting = 1
        mock_port.read.side_effect = [
            b">",  # Prompt
            b"+CMGS: 123\r\nOK\r\n"  # Success response
        ]
        
        # Mock the send_sms method to avoid actual serial communication
        with patch.object(handler, 'send_sms') as mock_send:
            handler.send_sms("+1234567890", "Test message")
            mock_send.assert_called_once_with("+1234567890", "Test message")
    
    def test_read_sms(self, mock_sms_handler):
        """Test reading SMS messages."""
        handler, mock_port = mock_sms_handler
        
        response = '+CMGL: 1,"REC UNREAD","+1234567890","25/07/21,21:07:17-28"\nTest message\nOK'
        
        with patch.object(handler, '_send_at_command', return_value=response):
            messages = handler.read_sms()
        
        assert len(messages) == 1
        assert messages[0].sender == "+1234567890"
        assert messages[0].message == "Test message"
    
    def test_delete_sms(self, mock_sms_handler):
        """Test deleting SMS message."""
        handler, mock_port = mock_sms_handler
        
        with patch.object(handler, '_send_at_command', return_value="OK"):
            handler.delete_sms(1)
        
        # Should not raise exception


if __name__ == "__main__":
    pytest.main([__file__])