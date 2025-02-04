import pygame
import socket
import sys
import json

pygame.init()
clock = pygame.time.Clock()

# Get server IP and port from command-line arguments
if len(sys.argv) < 2:
    print("Usage: python client.py <SERVER_IP> [PORT]")
    sys.exit(1)

SERVER_IP = sys.argv[1]  # IP address from command line
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 12345  # Default port if not provided


def controller(client: socket):
    joysticks = {}
    while True:
        # Possible joystick events: JOYAXISMOTION, JOYBALLMOTION, JOYBUTTONDOWN,
        # JOYBUTTONUP, JOYHATMOTION, JOYDEVICEADDED, JOYDEVICEREMOVED
        messages = []

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                messages.append(f"Joystick button {event.button} pressed.")
            if event.type == pygame.JOYBUTTONUP:
                messages.append(f"Joystick button {event.button} released.")
            if event.type == pygame.JOYAXISMOTION:
                messages.append(f"Joystick movement: Degree {event.value}, Axis {event.axis}")

            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                messages.append(f"Joystick {joy.get_instance_id()} connencted")
            if event.type == pygame.JOYDEVICEREMOVED:
                del joysticks[event.instance_id]
                messages.append(f"Joystick {event.instance_id} disconnected")

            bundled_messages = '\n'.join(str(message) for message in messages)  
            print(bundled_messages)
            client.sendall(bundled_messages.encode())
def main():
    # Create and configure socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"Connecting to {SERVER_IP}:{PORT}...")
        client_socket.connect((SERVER_IP, PORT))
        print("Connected successfully!")

        while True:
            try:
                controller(client_socket)
            except BrokenPipeError:
                print("Connection lost. Unable to send message.")
                break

    except socket.error as e:
        print(f"Connection error: {e}")

    finally:
        client_socket.close()
        print("Client shut down.")



if __name__ == "__main__":
    main()
