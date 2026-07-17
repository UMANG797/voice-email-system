#!/bin/bash
set -e
echo "Setting up Voice-Based Email System..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "IMPORTANT: A .env file was created from .env.example."
    echo "Please open .env and set SECRET_KEY and FERNET_KEY before running the app."
    echo "See README.md for the exact commands to generate them."
    echo ""
fi

echo "Setup complete. Run ./run.sh to start the app."
