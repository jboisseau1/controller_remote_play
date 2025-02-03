import socket
import struct
import evdev
import os
import threading

# Get host and port from environment variables
HOST = os.getenv("CONTROLLER_HOST", "0.0.0.0")  # Default to listening on all interfaces
PORT = int(os.getenv("CONTROLLER_PORT", 5555))

def find_controller():
    """Find an Xbox or gamepad controller connected to the system."""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if 'Xbox' in device.name or 'Gamepad' in device.name:
            print(f"✅ Using controller: {device.name} ({device.path})")
            return device
    return None

def send_controller_data(device):
    """Read controller input and send it over UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    with device.grab_context():  # Prevents system from using controller
        for event in device.read_loop():
            if event.type in [evdev.ecodes.EV_ABS, evdev.ecodes.EV_KEY]:
                data = struct.pack("IHHI", event.sec, event.usec, event.type, event.code, event.value)
                sock.sendto(data, (HOST, PORT))

if __name__ == "__main__":
    controller = find_controller()
    if controller:
        print(f"🚀 Starting controller server on {HOST}:{PORT}...")
        send_controller_data(controller)
    else:
        print("❌ No compatible controller found. Exiting.")
