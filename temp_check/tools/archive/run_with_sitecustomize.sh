#!/usr/bin/env bash
set -e
export PYTHONPATH=".:$PYTHONPATH"
echo "[sitecustomize] PYTHONPATH=$PYTHONPATH"
python "$@"
