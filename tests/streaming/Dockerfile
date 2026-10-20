ARG BASE_IMAGE=rampi-remote-test
FROM ${BASE_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake build-essential pkg-config libopus-dev libevdev-dev libudev-dev \
    libsdl2-dev libavcodec-dev libavutil-dev libasound2-dev libcurl4-openssl-dev \
    libssl-dev libexpat1-dev libavahi-client-dev uuid-dev curl ca-certificates
# Official Sunshine package, pinned by release and publisher-provided asset digest.
RUN architecture="$(dpkg --print-architecture)" \
    && case "$architecture" in \
       amd64) digest=a86f858cbae57f60ecebd445402ee0295c1c057b857bd45d44c2ea2d255cbbfb ;; \
       arm64) digest=45f250a6bae3629bd67d6856356e5d838569fbe4f6128440124c727a3d5fef5e ;; \
       *) exit 1 ;; esac \
    && curl -fL "https://github.com/LizardByte/Sunshine/releases/download/v2026.914.233613/sunshine_2026.914.233613-1%2Bdebiantrixie_${architecture}.deb" -o /tmp/sunshine.deb \
    && echo "$digest  /tmp/sunshine.deb" | sha256sum -c - \
    && apt-get install -y /tmp/sunshine.deb && rm /tmp/sunshine.deb
# Exactly the upstream SDL/FFmpeg build used by the optional Pi installer.
RUN git clone https://github.com/moonlight-stream/moonlight-embedded.git /build/moonlight \
    && git -C /build/moonlight checkout --detach 775444287305849ebdf4736c75298ad0713e2d5d \
    && git -C /build/moonlight submodule update --init --recursive \
    && cmake -S /build/moonlight -B /build/output -DCMAKE_BUILD_TYPE=Release \
       -DENABLE_SDL=ON -DENABLE_FFMPEG=ON -DENABLE_X11=OFF -DENABLE_CEC=OFF -DENABLE_PULSE=OFF \
    && cmake --build /build/output --parallel 2 && cmake --install /build/output && ldconfig
USER rampi
