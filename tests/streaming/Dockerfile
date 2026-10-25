ARG BASE_IMAGE=rampi-remote-test
FROM ${BASE_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake build-essential pkg-config libopus-dev libevdev-dev libudev-dev \
    libsdl2-dev libavcodec-dev libavutil-dev libasound2-dev libcurl4-openssl-dev \
    libssl-dev libexpat1-dev libavahi-client-dev uuid-dev curl ca-certificates \
    pulseaudio pulseaudio-utils
COPY tests/streaming/install-sunshine.sh /tmp/install-sunshine.sh
RUN RAMPI_FIXTURE_BUILD=1 sh /tmp/install-sunshine.sh && rm /tmp/install-sunshine.sh
# Exactly the upstream SDL/FFmpeg build used by the optional Pi installer.
RUN git clone https://github.com/moonlight-stream/moonlight-embedded.git /build/moonlight \
    && git -C /build/moonlight checkout --detach 775444287305849ebdf4736c75298ad0713e2d5d \
    && git -C /build/moonlight submodule update --init --recursive \
    && cmake -S /build/moonlight -B /build/output -DCMAKE_BUILD_TYPE=Release \
       -DENABLE_SDL=ON -DENABLE_FFMPEG=ON -DENABLE_X11=OFF -DENABLE_CEC=OFF -DENABLE_PULSE=OFF \
    && cmake --build /build/output --parallel 2 && cmake --install /build/output && ldconfig
USER rampi
