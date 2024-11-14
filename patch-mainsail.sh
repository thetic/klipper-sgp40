#!/usr/bin/env bash

MAINSAIL_PATH=${HOME}/mainsail

usage() {
    echo "Usage: $0 [-m <mainsail_path>]" 1>&2
    exit 1
}
# Parse command line arguments
while getopts "m:h" arg; do
    case $arg in
    m) MAINSAIL_PATH=$OPTARG ;;
    *) usage ;;
    esac
done

grep -l -R additionalSensors -- "${MAINSAIL_PATH}" | xargs sed -i 's+additionalSensors=\[+additionalSensors=\["sgp40",+g'
