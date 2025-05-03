#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Setting WeasyPrint library path..."
# Construct the DYLD_LIBRARY_PATH using brew --prefix
# Add error checking for brew command
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew (brew) command not found. Please install Homebrew."
    exit 1
fi

FONTCONFIG_LIB="$(brew --prefix fontconfig)/lib"
HARFBUZZ_LIB="$(brew --prefix harfbuzz)/lib"
GLIB_LIB="$(brew --prefix glib)/lib"
PANGO_LIB="$(brew --prefix pango)/lib"
CAIRO_LIB="$(brew --prefix cairo)/lib"

# Check if prefixes were found
if [[ -z "$GLIB_LIB" || ! -d "$GLIB_LIB" ]]; then
     echo "Error: Could not find Homebrew prefix or lib directory for glib. Is it installed?"
     exit 1
fi
# Add checks for other libraries as needed...

export DYLD_LIBRARY_PATH="$FONTCONFIG_LIB:$HARFBUZZ_LIB:$GLIB_LIB:$PANGO_LIB:$CAIRO_LIB${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
echo "DYLD_LIBRARY_PATH set to: $DYLD_LIBRARY_PATH"

# Activate virtual environment if it exists in the script's directory
VENV_PATH="$SCRIPT_DIR/venv"
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    echo "Warning: venv directory not found at $VENV_PATH. Assuming dependencies are installed globally or venv is already active."
fi

# Run the Flask app using the Python from the activated venv (or path)
echo "Starting Flask application (app.py)..."
# Use python from venv if activated, otherwise assume python is in PATH
if [ -d "$VENV_PATH" ]; then
    "$VENV_PATH/bin/python" "$SCRIPT_DIR/app.py"
else
    python "$SCRIPT_DIR/app.py"
fi 