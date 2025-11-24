
from _smoke_common import ensure_sys_path, export_env_if_any, discord_get_message, extract_json_from_text
import os

ensure_sys_path()
export_env_if_any()  # <<< load .env / hybrid before reading env vars

ch = int(os.getenv("XP_STATUS_CHANNEL_ID", "0") or "0")
msg = int(os.getenv("XP_STATUS_MESSAGE_ID", "0") or "0")
tok = bool(os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN"))

if not (ch and msg and tok):
    print("[PINNED] set XP_STATUS_CHANNEL_ID & XP_STATUS_MESSAGE_ID & DISCORD_BOT_TOKEN")
    raise SystemExit(2)

data = discord_get_message(ch, msg)
if not data:
    print("[PINNED] not accessible")
    raise SystemExit(2)

content = data.get("content") or ""
j = extract_json_from_text(content)
print("[PINNED content has JSON?]", bool(j))
print("[EMBEDS count]", len(data.get("embeds") or []))
print("[OK]")
