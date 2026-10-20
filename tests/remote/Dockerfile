ARG BASE_IMAGE=rampi-trixie-test
FROM ${BASE_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    xrdp xorgxrdp freerdp3-x11 xterm x11-xserver-utils dbus-x11 openssl \
    && rm -rf /var/lib/apt/lists/*
USER rampi
