#!/usr/bin/env bash
# ==============================================================================
# Setup 8GB Swap File to prevent Out-Of-Memory (OOM) process kills
# ==============================================================================
set -euo pipefail

SWAP_PATH="/swapfile"
SWAP_SIZE="8G"

echo "=== Setting up ${SWAP_SIZE} Swapfile ==="

# Check if swapfile already exists or is active
if swapon --show | grep -q "${SWAP_PATH}"; then
    echo "Swapfile at ${SWAP_PATH} is already active."
    free -h
    exit 0
fi

if [ -f "${SWAP_PATH}" ]; then
    echo "Existing ${SWAP_PATH} found, turning on..."
    sudo chmod 600 "${SWAP_PATH}"
    sudo mkswap "${SWAP_PATH}"
    sudo swapon "${SWAP_PATH}"
else
    echo "Allocating ${SWAP_SIZE} at ${SWAP_PATH}..."
    sudo fallocate -l "${SWAP_SIZE}" "${SWAP_PATH}"
    sudo chmod 600 "${SWAP_PATH}"
    echo "Formatting swap..."
    sudo mkswap "${SWAP_PATH}"
    echo "Enabling swap..."
    sudo swapon "${SWAP_PATH}"
fi

# Add to /etc/fstab if not already present
if ! grep -q "${SWAP_PATH}" /etc/fstab; then
    echo "Adding ${SWAP_PATH} entry to /etc/fstab for persistence..."
    echo "${SWAP_PATH} none swap sw 0 0" | sudo tee -a /etc/fstab
fi

# Set optimal vm.swappiness (e.g., 10 or 20 for development desktops)
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=20" | sudo tee -a /etc/sysctl.conf
    sudo sysctl vm.swappiness=20
fi

echo "=== Swap Configuration Complete ==="
swapon --show
free -h

