#!/usr/bin/env bash
# Single-node Wazuh install for the lab (indexer + server + dashboard) on Ubuntu 24.04 (wazuh01).
#
# Pinned: Wazuh 4.14.8. The official installer is downloaded and its SHA-256 is checked before it runs;
# if Wazuh publishes a new 4.14.x installer the hash changes and this script stops, so the lab stays
# reproducible. To move to a new version, update both values below after reviewing the release notes.
set -euo pipefail

WAZUH_MAJOR="4.14"
WAZUH_VERSION="4.14.8"
INSTALLER_SHA256="9adb693c474317644358fef74e629b0fab782bcb9c1a411e967a8348e3830bc1"
INSTALLER_URL="https://packages.wazuh.com/${WAZUH_MAJOR}/wazuh-install.sh"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo $0)." >&2
  exit 1
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

echo "[*] Downloading Wazuh ${WAZUH_VERSION} installer"
curl -fsSL "$INSTALLER_URL" -o wazuh-install.sh

echo "[*] Verifying installer checksum"
echo "${INSTALLER_SHA256}  wazuh-install.sh" | sha256sum --check --status || {
  echo "Checksum mismatch: the installer at ${INSTALLER_URL} is not the pinned ${WAZUH_VERSION} release." >&2
  echo "Review the new release, then update WAZUH_VERSION and INSTALLER_SHA256 in this script." >&2
  exit 1
}

grep -q "readonly wazuh_version=\"${WAZUH_VERSION}\"" wazuh-install.sh || {
  echo "Installer does not declare version ${WAZUH_VERSION}." >&2
  exit 1
}

echo "[*] Installing Wazuh ${WAZUH_VERSION} all-in-one"
bash ./wazuh-install.sh -a

echo "[*] Done. The generated admin password is printed above and saved in wazuh-install-files.tar."
echo "    Store it in your password manager. Never commit it to this repository."
