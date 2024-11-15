#!/usr/bin/env bash

# Force script to exit if an error occurs
set -e

KLIPPER_PATH="${HOME}/klipper"
KLIPPER_SERVICE_NAME=klipper
MOONRAKER_CONFIG_DIR="${HOME}/printer_data/config"

# Fall back to old directory for configuration as default
if [ ! -d "${MOONRAKER_CONFIG_DIR}" ]; then
    echo "\"$MOONRAKER_CONFIG_DIR\" does not exist. Falling back to "${HOME}/klipper_config" as default."
    MOONRAKER_CONFIG_DIR="${HOME}/klipper_config"
fi

usage() {
    echo "Usage: $0 [-k <klipper path>] [-s <klipper service name>] [-c <configuration path>] [-u]" 1>&2
    exit 1
}
# Parse command line arguments
while getopts "k:s:c:uh" arg; do
    case $arg in
    k) KLIPPER_PATH=$OPTARG ;;
    s) KLIPPER_SERVICE_NAME=$OPTARG ;;
    c) MOONRAKER_CONFIG_DIR=$OPTARG ;;
    u) UNINSTALL=1 ;;
    h) usage ;;
    esac
done

# Find SRCDIR from the pathname of this script
SRCDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/src/ && pwd)"

# Verify Klipper has been installed
check_klipper() {
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F "$KLIPPER_SERVICE_NAME.service")" ]; then
        echo "Klipper service found with name "$KLIPPER_SERVICE_NAME"."
    else
        echo "[ERROR] Klipper service with name "$KLIPPER_SERVICE_NAME" not found, please install Klipper first or specify name with -s."
        exit -1
    fi
}

check_folders() {
    if [ ! -d "$KLIPPER_PATH/klippy/extras/" ]; then
        echo "[ERROR] Klipper installation not found in directory \"$KLIPPER_PATH\". Exiting"
        exit -1
    fi
    echo "Klipper installation found at $KLIPPER_PATH"

    if [ ! -f "${MOONRAKER_CONFIG_DIR}/moonraker.conf" ]; then
        echo "[ERROR] Moonraker configuration not found in directory \"$MOONRAKER_CONFIG_DIR\". Exiting"
        exit -1
    fi
    echo "Moonraker configuration found at $MOONRAKER_CONFIG_DIR"
}

# Link extension to Klipper
link_extension() {
    echo -n "Linking extension to Klipper... "
    ln -sf "${SRCDIR}/sgp40.py" "${KLIPPER_PATH}/klippy/extras/sgp40.py"
    ln -sf "${SRCDIR}/voc_algorithm.py" "${KLIPPER_PATH}/klippy/extras/voc_algorithm.py"
    echo "[OK]"
}

# Restart moonraker
restart_moonraker() {
    echo -n "Restarting Moonraker... "
    sudo systemctl restart moonraker
    echo "[OK]"
}

# Add updater to moonraker.conf
add_updater() {
    echo -e -n "Adding update manager to moonraker.conf... "

    update_section=$(grep -c '\[update_manager klipper-sgp40\]' ${MOONRAKER_CONFIG_DIR}/moonraker.conf || true)
    if [ "${update_section}" -eq 0 ]; then
        echo -e "\n" >>${MOONRAKER_CONFIG_DIR}/moonraker.conf
        while read -r line; do
            echo -e "${line}" >>${MOONRAKER_CONFIG_DIR}/moonraker.conf
        done <"$PWD/file_templates/moonraker.conf"
        echo -e "\n" >>${MOONRAKER_CONFIG_DIR}/moonraker.conf
        echo "[OK]"
        restart_moonraker
    else
        echo -e "[update_manager klipper-sgp40] already exists in moonraker.conf [SKIPPED]"
    fi
}

restart_klipper() {
    echo -n "Restarting Klipper... "
    sudo systemctl restart $KLIPPER_SERVICE_NAME
    echo "[OK]"
}

start_klipper() {
    echo -n "Starting Klipper... "
    sudo systemctl start $KLIPPER_SERVICE_NAME
    echo "[OK]"
}

stop_klipper() {
    echo -n "Stopping Klipper... "
    sudo systemctl stop $KLIPPER_SERVICE_NAME
    echo "[OK]"
}

uninstall() {
    echo -n "Uninstalling... "

    rm -f "${KLIPPER_PATH}/klippy/extras/sgp40.py"
    rm -f "${KLIPPER_PATH}/klippy/extras/voc_algorithm.py"

    echo "[OK]"
    echo "You can now remove the [update_manager klipper-sgp40] section in your moonraker.conf and delete this directory. Also remove all sgp40 configurations from your Klipper configuration."
}

# Helper functions
verify_ready() {
    if [ "$EUID" -eq 0 ]; then
        echo "[ERROR] This script must not run as root. Exiting."
        exit -1
    fi
}

# Run steps
verify_ready
check_klipper
check_folders
stop_klipper
if [ ! $UNINSTALL ]; then
    link_extension
    add_updater
else
    uninstall
fi
start_klipper
