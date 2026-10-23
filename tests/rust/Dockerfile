FROM rust:1.98-slim-trixie@sha256:4cd829461bd5c4d511c32e269da9cb8929223b666519d8004e35fc8d1d771ab7
ENV DEBIAN_FRONTEND=noninteractive CARGO_TARGET_DIR=/build/target
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-4-dev libvte-2.91-gtk4-dev libwebkitgtk-6.0-dev libnm-dev \
    labwc libglib2.0-bin dbus-daemon fonts-dejavu-core grim wtype wayland-utils procps shellcheck \
    network-manager bluez wlr-randr libcanberra0 pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN useradd --create-home --uid 1000 rampi
RUN rustup component add clippy rustfmt
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-common libgtk-4-media-gstreamer \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends python3-dbusmock pulseaudio \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends gstreamer1.0-pulseaudio \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends libcanberra-dev libcanberra-pulse \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends wireguard-tools iproute2 iputils-ping polkitd \
    && rm -rf /var/lib/apt/lists/*
COPY tests/rust/install-test-tailscale.py /tmp/install-test-tailscale.py
RUN python3 /tmp/install-test-tailscale.py && install -d -o rampi -g rampi -m 700 /run/tailscale
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client openssh-server pamtester python3-pil wlrctl \
    && install -d -m 755 /run/sshd && rm -rf /var/lib/apt/lists/*
