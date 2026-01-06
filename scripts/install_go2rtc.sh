#!/usr/bin/env bash

set -euo pipefail

# Install the go2rtc binary in the devcontainer so Home Assistant can find it.
if command -v go2rtc >/dev/null 2>&1; then
    echo "go2rtc already installed at $(command -v go2rtc)"
    exit 0
fi

arch="$(uname -m)"
case "$arch" in
    x86_64|amd64) asset="go2rtc_linux_amd64" ;;
    arm64|aarch64) asset="go2rtc_linux_arm64" ;;
    armv7l|armv7) asset="go2rtc_linux_arm" ;;
    armv6l) asset="go2rtc_linux_armv6" ;;
    i386|i686) asset="go2rtc_linux_i386" ;;
    *)
        echo "Unsupported architecture: ${arch}" >&2
        exit 1
        ;;
esac

tag="$(
    curl -fsSL https://api.github.com/repos/AlexxIT/go2rtc/releases/latest |
        python3 -c 'import json,sys; data=json.load(sys.stdin); print(data.get("tag_name","").strip())'
)"

if [ -z "${tag}" ]; then
    echo "Unable to determine go2rtc release tag" >&2
    exit 1
fi

url="https://github.com/AlexxIT/go2rtc/releases/download/${tag}/${asset}"
tmp="$(mktemp)"
echo "Downloading ${url} ..."
curl -fsSL "${url}" -o "${tmp}"

install_path="/usr/local/bin/go2rtc"
if [ -w "$(dirname "${install_path}")" ]; then
    install -m 755 "${tmp}" "${install_path}"
else
    sudo install -m 755 "${tmp}" "${install_path}"
fi
rm -f "${tmp}"

echo "Installed go2rtc to ${install_path}"
