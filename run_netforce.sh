#!/bin/bash

# Define paths
VENV_DIR="$HOME/Desktop/Netforce/venv"
SCRIPT_PATH="$HOME/Desktop/Netforce/web_scrapper_v2.py"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Run the Python script
python "$SCRIPT_PATH"

# Deactivate the virtual environment when done
