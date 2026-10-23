FROM debian:trixie@sha256:913f6706df59a68922d1dd08f78c2476560a8d367897200a6005b00e5f67c2d5
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    qemu-system-x86 qemu-system-arm qemu-efi-aarch64 qemu-utils cloud-image-utils \
    ca-certificates curl python3 python3-yaml xorriso \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
CMD ["python3", "scripts/test-virtual-linux.py"]
