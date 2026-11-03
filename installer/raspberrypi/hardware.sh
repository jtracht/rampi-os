#!/bin/bash
# Raspberry Pi OS arm64 supplies model-specific kernels and drivers.
# Do not infer capability from a revision number or force boot/GPU options.
rampi_supported_model() {
    case "$1" in
        'Raspberry Pi 3 Model '*|'Raspberry Pi 4 Model '*|'Raspberry Pi 5 Model '*|'Raspberry Pi 400 '*|'Raspberry Pi 500 '*|'Raspberry Pi Compute Module 3 '*|'Raspberry Pi Compute Module 4 '*|'Raspberry Pi Compute Module 4S '*|'Raspberry Pi Compute Module 5 '*|'Raspberry Pi Zero 2 W '*) return 0 ;;
        *) return 1 ;;
    esac
}
