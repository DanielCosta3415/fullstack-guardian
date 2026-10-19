#!/usr/bin/env bash
# Only the explicitly dispatched disposable GitHub-hosted acceptance machine.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_ENVIRONMENT:-}" == github-hosted ]] || { echo 'Disposable GitHub-hosted runner required'; exit 2; }
[[ $(id -u) != 0 && $(uname -m) == x86_64 ]] || exit 2
trap 'echo "Hosted grader setup failed at line $LINENO; no fallback to rootful grading" >&2' ERR
if ! command -v newuidmap >/dev/null || ! command -v newgidmap >/dev/null; then
  # Signed distribution packages, installed only in this disposable machine.
  sudo apt-get update -qq
  sudo apt-get install -y uidmap dbus-user-session
fi
if ! command -v dockerd-rootless-setuptool.sh >/dev/null; then
  # Runner images can ship Moby without Docker's rootless extras/repository.
  # Bootstrap only the official signed repository, with an exact reviewed key.
  key_path="$RUNNER_TEMP/guardian-docker.asc"
  curl --proto '=https' --tlsv1.2 -fsSL https://download.docker.com/linux/ubuntu/gpg -o "$key_path"
  fingerprint=$(gpg --show-keys --with-colons "$key_path" | awk -F: '$1=="fpr" {print $10; exit}')
  [[ "$fingerprint" == 9DC858229FC7DD38854AE2D88D81803C0EBFCD88 ]] || { echo 'Docker signing key identity changed; review required'; exit 2; }
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo install -m 0644 "$key_path" /etc/apt/keyrings/guardian-docker.asc
  suite=$(. /etc/os-release; printf '%s' "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
  [[ "$suite" == noble ]] || exit 2
  printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/guardian-docker.asc\n' "$suite" | sudo tee /etc/apt/sources.list.d/guardian-docker.sources >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y docker-ce-rootless-extras=5:29.8.2-1~ubuntu.24.04~noble
fi
dpkg-query -W uidmap dbus-user-session docker-ce-rootless-extras
[[ -f /sys/fs/cgroup/cgroup.controllers ]] || exit 2
# Configure delegation only in this ephemeral VM, never on a user's machine.
sudo mkdir -p /etc/systemd/system/user@.service.d
printf '[Service]\nDelegate=cpu cpuset io memory pids\n' | sudo tee /etc/systemd/system/user@.service.d/guardian-delegate.conf >/dev/null
sudo systemctl daemon-reload
sudo loginctl enable-linger "$(id -un)"
sudo systemctl start "user@$(id -u).service"
sudo systemctl set-property "user@$(id -u).service" 'Delegate=cpu cpuset io memory pids'
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
dockerd-rootless-setuptool.sh install --force
systemctl --user start docker
export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/docker.sock"
python -c 'import json,subprocess; x=json.loads(subprocess.check_output(["docker","info","--format","{{json .SecurityOptions}}"])); assert any("rootless" in s for s in x)'
image=$(python -c 'import json; print(json.load(open("core/grader-image-v1.json"))["image"])')
# Explicit, digest-pinned provisioning step; the grading API itself never pulls.
docker pull --platform linux/amd64 "$image"
printf 'DOCKER_HOST=%s\nGUARDIAN_GRADER_IMAGE=%s\n' "$DOCKER_HOST" "$image" >> "$GITHUB_ENV"
