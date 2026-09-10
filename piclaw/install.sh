#!/bin/bash
# PiClaw install script for Raspberry Pi
set -e

echo "=== PiClaw Installer ==="

# 1. Python deps
pip3 install --user requests psutil

# 2. Copy .env if not exists
if [ ! -f ../.env ] && [ ! -f .env ]; then
    cp ../.env.example .env
    echo "Created .env — edit with your API key: nano .env"
fi

# 3. Copy config if not exists
if [ ! -f piclaw.json ]; then
    echo "piclaw.json already exists — skipping"
fi

# 4. Create data dirs
mkdir -p data/memory data/tasks data/rules data/devices

# 5. Optional: install systemd service
read -p "Install systemd service (auto-start on boot)? [y/N] " ans
if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    sudo cp piclaw.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable piclaw
    echo "Service installed. Start with: sudo systemctl start piclaw"
fi

echo ""
echo "=== PiClaw installed ==="
echo "Run from project root: python3 -m piclaw"
