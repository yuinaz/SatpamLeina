#!/usr/bin/env bash
set -euo pipefail
file="$1"

HELPER='''import logging

def _install_health_log_filter():
    try:
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        pass  # never break app on logging issues
'''

if ! grep -q '_install_health_log_filter' "$file"; then
  tmp="$(mktemp)"
  printf "%s\n" "$HELPER" > "$tmp"
  cat "$file" >> "$tmp"
  mv -f "$tmp" "$file"
  echo "  + helper added to $(basename "$file")"
fi

# Ensure call exists inside create_app() after app = Flask(...)
if grep -q 'def create_app' "$file" && ! grep -q '_install_health_log_filter()' "$file"; then
  perl -0777 -pe 's/(def\s+create_app\([^)]*\):[\s\S]{0,400}?\n\s*app\s*=\s*Flask\([^)]*\))/\1\n    _install_health_log_filter()/m' -i "$file" || true
  # Fallback: insert at start of function if pattern above fails
  if ! grep -q '_install_health_log_filter()' "$file"; then
    perl -0777 -pe 's/(def\s+create_app\([^)]*\):)/\1\n    _install_health_log_filter()/m' -i "$file" || true
  fi
  echo "  + install() call added in $(basename "$file")"
fi
