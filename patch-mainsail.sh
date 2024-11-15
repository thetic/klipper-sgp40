#!/usr/bin/env bash

MAINSAIL_PATH=${HOME}/mainsail

usage() {
    echo "Usage: $0 [-m <mainsail_path>]" 1>&2
}

# Parse command line arguments
while getopts "m:h" arg; do
    case $arg in
    m) MAINSAIL_PATH=$OPTARG ;;
    h) usage ;;
    *)
        usage
        exit 1
        ;;
    esac
done

grep -lRZ additionalSensors -- "${MAINSAIL_PATH}" | xargs -0 sed -i -e 's/,"htu21d"/\0,"sgp40"/g' -e 's/\(,"sgp40"\)\+/\1/g'
