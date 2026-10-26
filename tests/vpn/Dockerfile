ARG SDK_IMAGE=rampi-rust-dev
FROM ${SDK_IMAGE}
USER root
RUN if ! command -v iptables >/dev/null; then \
      apt-get update && apt-get install -y --no-install-recommends iptables \
      && rm -rf /var/lib/apt/lists/*; fi
COPY tests/vpn/install-headscale.py /tmp/install-headscale.py
RUN python3 /tmp/install-headscale.py && rm /tmp/install-headscale.py
WORKDIR /src
