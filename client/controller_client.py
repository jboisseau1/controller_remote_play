import socket
import struct
import evdev
import uinput
import os

# Get port from environment variable
PORT = int(os.getenv("LISTEN_PORT", 5555))

def receive_controller_data():
    """Listen for controller data over UDP and emulate input."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))  # Listen on all available interfaces

    # Create virtual controller
    device = uinput.Device([
        uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
        uinput.BTN_TL, uinput.BTN_TR, uinput.BTN_SELECT, uinput.BTN_START,
        uinput.ABS_X + (-32768, 32767, 0, 0),
        uinput.ABS_Y + (-32768, 32767, 0, 0),
        uinput.ABS_RX + (-32768, 32767, 0, 0),
        uinput.ABS_RY + (-32768, 32767, 0, 0)
    ])

    print(f"🎮 Listening for controller data on port {PORT}...")

    while True:
        data, _ = sock.recvfrom(1024)
        sec, usec, type_, code, value = struct.unpack("IHHI", data)

        if type_ == evdev.ecodes.EV_KEY:
            device.emit(code, value)
        elif type_ == evdev.ecodes.EV_ABS:
            device.emit(code, value, syn=True)

if __name__ == "__main__":
    print("🚀 Starting virtual controller client...")
    receive_controller_data()
