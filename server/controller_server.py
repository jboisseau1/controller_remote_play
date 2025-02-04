import socket

# Server settings
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 12345       # Port number

# Create a socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)  # Listen for incoming connections

print(f"Server listening on {HOST}:{PORT}")

conn, addr = server_socket.accept()
print(f"Connected by {addr}")

while True:
    data = conn.recv(1024)
    if not data:
        break
    print(f"Received: {data.decode()}")

conn.close()
