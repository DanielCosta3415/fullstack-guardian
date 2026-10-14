#!/usr/bin/env bash
# Python existente; sem downloads, sudo ou alterações de PATH.
set -u
guardian_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
for guardian_python in python3 python; do
  if command -v "$guardian_python" >/dev/null 2>&1 && "$guardian_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
    if [ "$#" -eq 0 ]; then set -- --user; fi
    exec "$guardian_python" "$guardian_root/install.py" "$@"
  fi
done
printf '%s\n' 'Python 3.11+ não encontrado. Instale Python por um canal de sua confiança; nenhuma alteração foi aplicada.' >&2
exit 1
