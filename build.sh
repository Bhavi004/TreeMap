#!/usr/bin/env bash
# Render build script: installs Node.js deps, builds frontend, installs Python deps

set -e

# Extract mask data from archive
echo "Extracting mask data..."
cd data/south_delhi
tar -xzf masks.tar.gz
cd ../..
echo "Mask data extracted."

# Install Node.js dependencies and build frontend
npm install --legacy-peer-deps
npm run build

# Install Python dependencies
pip install -r requirements.txt
pip install gunicorn
