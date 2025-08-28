"""
Command-line interface for PySMS library.
"""

import signal
import threading
from typing import Optional
import typer
from .sms_handler import SMSHandler, SMS


class ChatUI:
    """Chat interface for SMS communication."""
    
    def __init__(self, phone_number: str, sms_handler: SMSHandler):
        self.phone_number = phone_number
        self.sms_handler = sms_handler
        self._lock = threading.Lock()
    
    def display_message(self, sender: str, message: str, timestamp: str):
        """Display a message with proper formatting."""
        with self._lock:
            # Clear current line and move cursor up
            typer.echo(f"\r\033[K", nl=False)
            
            # Display the message with colors
            typer.echo(f"📱 {sender} [{timestamp}]: {message}", color=typer.colors.GREEN)
            
            # Redraw prompt
            typer.echo("> ", nl=False)
    
    def handle_incoming_message(self, sms: SMS):
        """Handle incoming SMS messages."""
        # Show debug info if handler has debug enabled
        if hasattr(self.sms_handler, 'debug') and self.sms_handler.debug:
            print(f"\n[DEBUG] Received SMS from: {sms.sender} (target: {self.phone_number})")
            print(f"[DEBUG] Message: {sms.message}")
            print(f"[DEBUG] Date: {sms.date}")
        
        # Show the message (can be from any number for debugging)
        self.display_message(sms.sender, sms.message, sms.date)
        
        # Also show if this matches our target number
        if sms.sender == self.phone_number and hasattr(self.sms_handler, 'debug') and self.sms_handler.debug:
            print(f"[DEBUG] ✓ Message from target number!")
    
    def send_message(self, message: str) -> bool:
        """Send an SMS message."""
        if not message.strip():
            return True
        
        try:
            self.sms_handler.send_sms(self.phone_number, message)
            return True
        except Exception as e:
            typer.echo(f"❌ Failed to send message: {e}", color=typer.colors.RED)
            return False


app = typer.Typer(help="PySMS CLI - Interactive SMS chat interface")

@app.command()
def main(
    phone_number: str = typer.Argument(..., help="Target phone number for SMS chat"),
    port: str = typer.Option("/dev/ttyUSB2", "--port", "-p", help="Serial port for GSM modem"),
    baud_rate: int = typer.Option(115200, "--baud", "-b", help="Serial port baud rate"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output")
):
    """Start SMS chat with a phone number."""
    
    # Initialize SMS handler
    try:
        sms_handler = SMSHandler(port, baud_rate, debug=debug)
        typer.echo("📱 SMS Chat initialized successfully!", color=True)
        typer.echo(f"📞 Connected to phone number: {phone_number}")
        typer.echo(f"🔌 Serial port: {port} at {baud_rate} baud")
        typer.echo("💬 Type your messages and press Enter to send. Ctrl+C to exit.")
        typer.echo("\n📋 Commands:")
        typer.echo("  /quit or /exit - Exit the program")  
        typer.echo("  /multi - Enter multi-line mode (end with '.' on its own line)")
        if debug:
            typer.echo("  🐛 [DEBUG MODE ENABLED - Will show detailed SMS processing info]", color=typer.colors.YELLOW)
        typer.echo("-" * 50)
        
    except Exception as e:
        typer.echo(f"❌ Failed to initialize SMS handler: {e}", err=True, color=typer.colors.RED)
        raise typer.Exit(1)
    
    # Create chat UI
    chat = ChatUI(phone_number, sms_handler)
    
    # Start listening for incoming SMS
    sms_handler.listen_for_incoming_sms(chat.handle_incoming_message)
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        typer.echo("\n🛑 Shutting down...")
        sms_handler.close()
        raise typer.Exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Main input loop
    typer.echo("> ", nl=False)
    
    try:
        while True:
            try:
                user_input = input().strip()
                
                if user_input in ["/quit", "/exit"]:
                    break
                
                if user_input == "/multi":
                    typer.echo("📝 Multi-line mode: Type your message, end with a line containing only '.' to send")
                    lines = []
                    typer.echo("| ", nl=False)
                    
                    while True:
                        line = input()
                        if line.strip() == ".":
                            break
                        lines.append(line)
                        typer.echo("| ", nl=False)
                    
                    if lines:
                        multi_message = "\n".join(lines)
                        if not chat.send_message(multi_message):
                            typer.echo("❌ Error sending message", color=typer.colors.RED)
                    
                    typer.echo("> ", nl=False)
                    continue
                
                if not user_input:
                    typer.echo("> ", nl=False)
                    continue
                
                if not chat.send_message(user_input):
                    typer.echo("❌ Error sending message", color=typer.colors.RED)
                
                typer.echo("> ", nl=False)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    finally:
        sms_handler.close()


def cli_main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    cli_main()