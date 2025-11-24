"""
Shared list + helper to skip non-chat channels during miners / learning update.
Import in your miners before pushing payloads.
"""
import os
import re

# Default skip list provided by user
DEFAULT_SKIP = {
    "763813761814495252",
    "936689852546678885",
    "767401659390623835",
    "1270611643964850178",
    "761163966482743307",
    "1422084695692414996",
    "1372983711771001064",
    "1378739739930398811",
}

_env = os.getenv("SATPAMBOT_SKIP_CHANNEL_IDS", "")
ENV_SKIP = {x.strip() for x in _env.split(",") if x.strip()}
SKIP_CHANNEL_IDS = DEFAULT_SKIP | ENV_SKIP

_re_channel = re.compile(r"/channels/\d+/(\d+)/")

def extract_channel_id(s: str) -> str | None:
    if not s:
        return None
    m = _re_channel.search(s)
    if m:
        return m.group(1)
    # also accept if s itself looks like a snowflake
    if s.isdigit() and len(s) >= 15:
        return s
    return None

def should_skip(url_or_id: str | None) -> bool:
    ch = extract_channel_id(url_or_id or "")
    return ch in SKIP_CHANNEL_IDS if ch else False