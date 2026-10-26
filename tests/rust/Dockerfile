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
RUN apt-get update && apt-get install -y --no-install-recommends git curl gnome-keyring libsecret-tools python3-graphql-core \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgstreamer-plugins-base1.0-dev libusbredirhost-dev libusbredirparser-dev libusb-1.0-0-dev libssl-dev sudo \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Model the actual native streaming runtime before offline installer/GUI tests.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-good \
    cmake build-essential pkg-config libopus-dev libevdev-dev libudev-dev libsdl2-dev \
    libavcodec-dev libavutil-dev libexpat1-dev libavahi-client-dev uuid-dev \
    && rm -rf /var/lib/apt/lists/*
# Reuse the same official C library and ABI as the existing streaming SDK.
# Build only its upstream target; do not install a second player or display.
RUN git clone https://github.com/moonlight-stream/moonlight-embedded.git /opt/moonlight-source \
    && git -C /opt/moonlight-source checkout --detach 775444287305849ebdf4736c75298ad0713e2d5d \
    && git -C /opt/moonlight-source submodule update --init --recursive \
    && test "$(git -C /opt/moonlight-source/third_party/moonlight-common-c rev-parse HEAD)" = b126e481a195fdc7152d211def17190e3434bcce \
    && cmake -S /opt/moonlight-source -B /opt/moonlight-build -DCMAKE_BUILD_TYPE=Release \
       -DENABLE_SDL=ON -DENABLE_FFMPEG=ON -DENABLE_X11=OFF -DENABLE_CEC=OFF -DENABLE_PULSE=OFF \
    && cmake --build /opt/moonlight-build --target moonlight-common --parallel 2 \
    && install -m 755 /opt/moonlight-build/libgamestream/libmoonlight-common.so.2.7.1 /usr/local/lib/ \
    && ldconfig
