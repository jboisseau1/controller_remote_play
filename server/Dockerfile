# Use a Raspberry Pi-compatible base image
FROM python:3.11-bullseye

# Install dependencies
RUN apt-get update && apt-get install -y \
    libevdev-dev \
    python3-pip \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install evdev

# Set working directory
WORKDIR /app

# Copy the script into the container
COPY controller_server.py /app/controller_server.py

# Grant necessary permissions
RUN chmod +x /app/controller_server.py

# Run the script when the container starts
CMD ["python", "/app/controller_server.py"]
