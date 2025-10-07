#!/bin/bash
set -e

VENV_DIR="venv"
REQ_FILE="requirements.txt"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ Virtual environment already exists."
fi

# Activate the venv
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
if [ -f "$REQ_FILE" ]; then
  echo "📦 Installing dependencies..."
  pip install -U pip
  pip install -r "$REQ_FILE"
else
  echo "⚠️ requirements.txt not found, skipping installation."
fi

# Run Django if manage.py exists
if [ -f "manage.py" ]; then
  echo "🚀 Running Django server..."
  python manage.py runserver
else
  echo "✅ Setup complete. To activate later, run:"
  echo "source $VENV_DIR/bin/activate"
fi
