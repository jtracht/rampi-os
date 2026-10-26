#!/bin/bash
set -euo pipefail
output=/opt/rampi/dependency-licenses
install -d -m 755 "$output/copyright"
cp -a /usr/share/doc/rampi/rust-licenses "$output/"
dpkg-query -W -f='${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n' > "$output/packages-and-sources.tsv"
while IFS=$'\t' read -r package _version _source _source_version; do
    name="${package%%:*}"
    if [[ -f "/usr/share/doc/$name/copyright" ]]; then
        cp -L "/usr/share/doc/$name/copyright" "$output/copyright/$name"
    fi
done < "$output/packages-and-sources.tsv"
if [[ -f /usr/share/doc/rampi/moonlight-embedded-2.7.1-source.tar.gz ]]; then
    cp /usr/share/doc/rampi/moonlight-embedded-2.7.1-source.tar.gz "$output/"
    cp /usr/share/doc/rampi/moonlight-LICENSE "$output/"
    cp /usr/share/doc/rampi/moonlight-runtime.sha256 /usr/share/doc/rampi/moonlight-source-revisions.txt /usr/share/doc/rampi/moonlight-source-files.sha256 "$output/"
fi
printf '%s\n' \
    'Third-party packages retain their individual licenses; see copyright/.' \
    'Exact Debian/Raspberry Pi source package names and versions are recorded in packages-and-sources.tsv.' \
    'Exact corresponding distro source archives accompany this image release in dependency-sources.tar.xz.' \
    'Their signed-index SHA256 metadata is recorded in debian-source-archives.json.' \
    'Original Cargo dependency license texts and Rust standard-library notices are included in rust-licenses/.' \
    > "$output/README.txt"
tar -cJf /opt/rampi/dependency-licenses.tar.xz -C /opt/rampi dependency-licenses
