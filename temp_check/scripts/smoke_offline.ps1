powershell -ExecutionPolicy Bypass -Command ^
  python scripts/smoke_qna_offline.py; ^
  echo ''; ^
  python scripts/smoke_xp_offline.py
