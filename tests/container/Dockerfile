FROM debian:trixie@sha256:913f6706df59a68922d1dd08f78c2476560a8d367897200a6005b00e5f67c2d5
ENV DEBIAN_FRONTEND=noninteractive QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    QT_QUICK_CONTROLS_STYLE=Basic PYTHONPATH=/app/client
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pytest python3-dbusmock python3-graphql-core python3-gi gir1.2-nm-1.0 libqt6svg6 qt6-svg-plugins openssh-client \
    python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtqml \
    python3-pyside6.qtquick python3-pyside6.qtquickcontrols2 python3-pyside6.qtdbus qml6-module-qtmultimedia \
    python3-pyside6.qttest qml6-module-qtquick qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts qml6-module-qtquick-window qml6-module-qtquick-shapes \
    qml6-module-qtquick-templates qml6-module-qtqml-workerscript fonts-dejavu-core time \
    accountsservice whois dbus systemd gnome-keyring libsecret-tools polkitd pamtester xvfb xauth xdotool openbox wmctrl x11-utils \
    network-manager wireguard-tools iproute2 iputils-ping pulseaudio pulseaudio-utils x11-xserver-utils x11-xkb-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY client client
COPY scripts scripts
COPY tests tests
COPY system system
COPY installer installer
COPY pyproject.toml .
RUN useradd --create-home --uid 1000 rampi
USER rampi
CMD ["bash", "-ec", "python3 -m pytest -q -p no:cacheprovider; python3 scripts/test-libnm.py; python3 scripts/test-ui.py; /usr/bin/time -v python3 -m rampi.app --smoke-test"]
