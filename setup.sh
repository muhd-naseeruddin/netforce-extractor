#!/bin/bash

# Define the Desktop path and Netforce directory
DESKTOP_PATH="$HOME/Desktop"
NETFORCE_DIR="$DESKTOP_PATH/netforce-extractor"
VENV_DIR="$NETFORCE_DIR/venv"

# Create the Netforce directory if it doesn’t exist
mkdir -p "$NETFORCE_DIR"

# Move into the Netforce directory
cd "$NETFORCE_DIR" || exit 1

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
    echo "Python3 is not installed. Please install Python3 before running this script."
    exit 1
fi

# Create a virtual environment in the Netforce directory
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Ensure pip is up to date
python3 -m pip install --upgrade pip

# Install packages from requirements.txt
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
else
    echo "requirements.txt not found. Please ensure it is in the Netforce directory."
    exit 1
fi

echo "Setup complete. To activate the environment, run: source $VENV_DIR/bin/activate"
echo "To run the script, use: python script.py"
