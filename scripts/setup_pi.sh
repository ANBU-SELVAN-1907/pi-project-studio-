#!/bin/bash
# ==============================================================================
# OmniRoute Luxury Phone OS - Raspberry Pi Zero W Deployment Script
# Configures ILI9341 SPI Display, XPT2046 Touch, I2S Mic & DAC Audio
# ==============================================================================

set -e

echo "=========================================================="
echo " Starting Installation of OmniRoute Luxury Phone OS      "
echo " Target: Raspberry Pi Zero W / 2.4\" TFT Touch (< 300MB)  "
echo "=========================================================="

# 1. Update OS Packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev python3-pygame libsdl2-dev \
    libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    python3-spidev python3-rpi.gpio alsa-utils libasound2-dev mpg123 portaudio19-dev

# A full 240x320 RGB565 frame is 153,600 bytes. Let spidev split one
# uninterrupted transaction in-kernel instead of forcing the Python loop to
# issue dozens of 4KB transfers per frame.
sudo install -d -m 755 /etc/modprobe.d
echo "options spidev bufsiz=65536" | sudo tee /etc/modprobe.d/spidev.conf >/dev/null

# 2. Install Python Dependencies
python3 -m pip install -r requirements.txt --break-system-packages

# 3. Configure ALSA for I2S INMP441 & MAX98357A
if [ -f "asound.conf" ]; then
    echo "Deploying I2S Audio ALSA configuration..."
    sudo cp asound.conf /etc/asound.conf
fi

# 4. Create local runtime directories with private permissions
mkdir -p gallery models data
chmod 700 gallery models data

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "Created .env from .env.example; fill in credentials before using online AI."
fi

echo "=========================================================="
echo " Installation Complete!                                   "
echo " Launch the OS with: python3 main.py                      "
echo "=========================================================="
