#!/bin/bash

# Define project directory and repository
PROJECT_DIR="$HOME/controller_remote_play"
REPO_URL="https://github.com/jboisseau1/controller_remote_play.git"  # CHANGE TO YOUR REPO

echo "🚀 Starting setup for Controller Remote Play..."

# Detect system type (server or client)
echo "🔍 Is this the (1) server (Raspberry Pi) or (2) client (receiving PC)?"
read -p "Enter 1 for server, 2 for client: " ROLE

if [ "$ROLE" -eq 1 ]; then
    INSTALL_SERVER=true
    INSTALL_CLIENT=false
    echo "🖥️ Configuring Raspberry Pi as the controller server..."
elif [ "$ROLE" -eq 2 ]; then
    INSTALL_SERVER=false
    INSTALL_CLIENT=true
    echo "🎮 Configuring this machine as the client..."
else
    echo "❌ Invalid selection. Exiting."
    exit 1
fi

# Update system
echo "🔄 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "📦 Installing necessary packages..."
sudo apt install -y docker.io docker-compose udev git

# Add user to Docker group (so Docker can run without sudo)
echo "👤 Adding current user to Docker group..."
sudo usermod -aG docker $USER

# Enable and start Docker
echo "⚙️ Enabling Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Clone the repository (or pull latest changes if it already exists)
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📥 Cloning repository..."
    git clone $REPO_URL $PROJECT_DIR
else
    echo "🔄 Repository already exists, pulling latest changes..."
    cd $PROJECT_DIR
    git pull
fi

cd $PROJECT_DIR

if [ "$INSTALL_SERVER" = true ]; then
    # Enable uinput module (needed for controller)
    echo "🎮 Enabling uinput module..."
    echo "uinput" | sudo tee -a /etc/modules
    sudo modprobe uinput

    # Set permissions for input devices
    echo "🔑 Configuring input device permissions..."
    sudo chmod 666 /dev/uinput
    sudo chmod -R 777 /dev/input

    # Make permissions persistent
    echo 'KERNEL=="uinput", MODE="0666"' | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger

    # Open UDP port for remote controller transmission
    echo "🛡️ Configuring firewall rules..."
    sudo ufw allow 5555/udp

    # Deploy the server container
    echo "🐳 Building and deploying the server container..."
    cd server
    docker-compose up --build -d

    # Add to crontab for automatic startup
    echo "⏳ Adding server to startup..."
    (crontab -l 2>/dev/null; echo "@reboot cd $PROJECT_DIR/server && docker-compose up -d") | crontab -

    echo "✅ Server setup complete!"
fi

if [ "$INSTALL_CLIENT" = true ]; then
    # Enable uinput module (for virtual controller)
    echo "🎮 Enabling uinput module..."
    echo "uinput" | sudo tee -a /etc/modules
    sudo modprobe uinput

    # Set permissions for virtual input device
    echo "🔑 Configuring input device permissions..."
    sudo chmod 666 /dev/uinput

    # Make permissions persistent
    echo 'KERNEL=="uinput", MODE="0666"' | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger

    # Deploy the client container
    echo "🐳 Building and deploying the client container..."
    cd client
    docker-compose up --build -d

    # Add to crontab for automatic startup
    echo "⏳ Adding client to startup..."
    (crontab -l 2>/dev/null; echo "@reboot cd $PROJECT_DIR/client && docker-compose up -d") | crontab -

    echo "✅ Client setup complete!"
fi

echo "🔄 Setup finished. You may need to restart for changes to take effect."
echo "🔄 Reboot now? (y/n)"
read response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo reboot
else
    echo "ℹ️ Remember to reboot manually for full effect!"
fi
