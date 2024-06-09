#!/bin/bash

set -euo pipefail

venv_dir=".venv"

if [ ! -d "$venv_dir" ]; then
    echo "🚧 Creating a new virtual environment..."
    python3 -m venv "$venv_dir"
fi

echo "🐍 Activating virtual environment..."
source "$venv_dir/bin/activate"


echo "📦 Installing requirements..."
pip install -r requirements.txt

# Create the database if it does not exist yet
if [ ! -e "database.db" ]; then
    echo "Database file not found. Creating the database..."
    set -x
    pushd src/
    python -m scripts.create_db
    popd
    set +x
fi

cd src/

echo ""
echo "✨ Starting the application at http://localhost:3000"
echo ""

APP_DEBUG=1 APP_PORT=3000 python app.py
