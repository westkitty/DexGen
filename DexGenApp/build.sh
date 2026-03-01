#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt
pip install pyinstaller

echo "Cleaning previous builds..."
rm -rf build dist "DexGen App.app"

echo "Building macOS .app bundle using PyInstaller..."
pyinstaller "DexGen App.spec" --clean

echo "Build complete! Find your app at dist/DexGen App.app"
