#!/usr/bin/env bash
set -e
python scripts/smoke_qna_offline.py
echo
python scripts/smoke_xp_offline.py
