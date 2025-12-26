#!/usr/bin/env bash
set -e

# Detect script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "=== Music Query Installer ==="

# 1. Check for Python and pip
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found. Please install it (sudo apt install python3)"
    exit 1
fi

if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
     # On some debian systems, pip might be missing or provided by python3-pip
    echo "Warning: pip/pip3 not found. Attempting to ensurepip..."
    # We might rely on venv creation which usually includes pip
fi

# Check for system beets (avoids compiling numpy/lap on ARM)
if ! command -v beet &> /dev/null; then
    echo "Warning: 'beet' command not found."
    echo "Installing beets from system repository to avoid compilation..."
    if command -v sudo &> /dev/null; then
        sudo apt update && sudo apt install -y beets
    else
        echo "Error: sudo not found. Please install beets manually:"
        echo "  apt install beets"
        exit 1
    fi
fi

# 2. Create virtual environment if it doesn't exist
# 2. Create virtual environment
if [ -d ".venv" ] && [ ! -f ".venv/bin/pip" ]; then
    echo "Virtual environment exists but pip is missing. Recreating..."
    rm -rf .venv
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if ! python3 -m venv .venv; then
        echo "Error: Failed to create virtual environment."
        echo "Make sure the 'venv' module is properly installed."
        echo "On Debian/Ubuntu/Armbian systems, run:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
else
    echo "Virtual environment already exists."
fi

# 3. Install dependencies
echo "Installing dependencies..."
./.venv/bin/python -m pip install -U pip
./.venv/bin/pip install -r requirements.txt

# 4. Generate systemd unit file
echo "Generating systemd service file..."
VENV_PATH="$SCRIPT_DIR/.venv"
APP_DIR="$SCRIPT_DIR"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/music-query.service"

mkdir -p "$SERVICE_DIR"

# Read template and substitute variables
# escape forward slashes for sed
ESCAPED_VENV_PATH=$(echo "$VENV_PATH" | sed 's/\//\\\//g')
ESCAPED_APP_DIR=$(echo "$APP_DIR" | sed 's/\//\\\//g')

sed -e "s/{{VENV_PATH}}/$ESCAPED_VENV_PATH/g" \
    -e "s/{{APP_DIR}}/$ESCAPED_APP_DIR/g" \
    "music-query.service.template" > "$SERVICE_FILE"

echo "Service file created at: $SERVICE_FILE"

# 5. Enable and start service
echo "Reloading systemd..."
systemctl --user daemon-reload
echo "Enabling music-query.service..."
systemctl --user enable music-query.service
echo "Starting music-query.service..."
systemctl --user restart music-query.service

echo "=== Installation Complete ==="
echo "You can check status with: systemctl --user status music-query"
echo "Logs can be viewed with: journalctl --user -u music-query -f"
