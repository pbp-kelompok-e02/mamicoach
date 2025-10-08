#!/bin/bash
set -e

VENV_DIR="env"
REQ_FILE="requirements.txt"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ Virtual environment already exists."
fi


# Activate the venv (check both possible locations)
if [ -f "$VENV_DIR/bin/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
  ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
else
  echo "ERROR: Cannot find activate script in bin or Scripts."
  exit 1
fi

# shellcheck disable=SC1090
source "$ACTIVATE_SCRIPT"

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
  echo "Preparing to run Django server..."
  python manage.py migrate
  echo "🚀 Running Django server..."
  python manage.py runserver
else
  echo "✅ Setup complete. To activate later, run:"
  echo "source $VENV_DIR/bin/activate"
fi
