#!/usr/bin/env bash

# Force script to exit if an error occurs
set -e

KLIPPER_PATH="${HOME}/klipper"
KLIPPER_SERVICE_NAME=klipper

SCRIPTS=(
    "sgp40.py"
    "voc_algorithm.py"
)

usage() {
    echo "Usage: $0 [-k <klipper path>] [-s <klipper service name>] [-c <configuration path>] [-u]" 1>&2
}

# Parse command line arguments
while getopts "k:s:c:uh" arg; do
    case $arg in
    k) KLIPPER_PATH=$OPTARG ;;
    s) KLIPPER_SERVICE_NAME=$OPTARG ;;
    u) UNINSTALL=1 ;;
    h) usage ;;
    *)
        usage
        exit 1
        ;;
    esac
done

# Find SRCDIR from the pathname of this script
SRCDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/src/ && pwd)"

# Verify Klipper has been installed
check_klipper() {
    if sudo systemctl list-units --full -all -t service --no-legend | grep -qF "$KLIPPER_SERVICE_NAME.service"; then
        echo "Klipper service found with name $KLIPPER_SERVICE_NAME."
    else
        echo "[ERROR] Klipper service with name $KLIPPER_SERVICE_NAME not found, please install Klipper first or specify name with -s."
        exit 1
    fi
}

check_folders() {
    if [ -d "$KLIPPER_PATH/klippy/extras/" ]; then
        echo "Klipper installation found at $KLIPPER_PATH"
    else
        echo "[ERROR] Klipper installation not found in directory $KLIPPER_PATH. Exiting"
        exit 1
    fi
}

# Link extension to Klipper
link_extension() {
    echo -n "Linking extension to Klipper... "
    for script in "${SCRIPTS[@]}"; do
        echo -n "${script}... "
        ln -sf "${SRCDIR}/${script}" "${KLIPPER_PATH}/klippy/extras/${script}"
    done
    echo "[OK]"
}

start_klipper() {
    echo -n "Starting Klipper... "
    sudo systemctl start "$KLIPPER_SERVICE_NAME"
    echo "[OK]"
}

stop_klipper() {
    echo -n "Stopping Klipper... "
    sudo systemctl stop "$KLIPPER_SERVICE_NAME"
    echo "[OK]"
}

uninstall() {
    echo -n "Uninstalling... "

    for script in "${SCRIPTS[@]}"; do
        echo -n "${script}... "
        rm -f "${KLIPPER_PATH}/klippy/extras/${script}"
    done

    echo "[OK]"
    echo "You can now remove the [update_manager klipper-sgp40] section in your moonraker.conf and delete this directory. Also remove all sgp40 configurations from your Klipper configuration."
}

# Helper functions
verify_ready() {
    if [ "$EUID" -eq 0 ]; then
        echo "[ERROR] This script must not run as root. Exiting."
        exit 1
    fi
}

# Run steps
verify_ready
check_klipper
check_folders
stop_klipper
if [ "$UNINSTALL" -eq 1 ]; then
    uninstall
else
    link_extension
fi
start_klipper
