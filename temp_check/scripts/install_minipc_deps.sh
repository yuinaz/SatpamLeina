#!/usr/bin/env bash
set -euo pipefail
echo "[deps] installing helper tools…"
unameOut="$(uname -s 2>/dev/null || echo '')"
case "${unameOut}" in
  Linux*)
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y jq python3 python3-pip
    elif command -v apk >/dev/null 2>&1; then
      sudo apk add --no-cache jq python3 py3-pip
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y jq python3 python3-pip
    fi
    ;;
  MINGW*|MSYS*)
    echo "Windows Git Bash detected. Install Python + jq via winget or choco:"
    echo "  winget install JQLang.jq"
    echo "  winget install Python.Python.3.10"
    ;;
  *)
    echo "Unknown OS; please install jq and Python manually."
    ;;
esac
