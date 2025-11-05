
import os, logging
from typing import List

log = logging.getLogger(__name__)

def _split_ids(s: str) -> List[int]:
    res: List[int] = []
    for part in (s or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            res.append(int(part))
        except Exception:
            pass
    return res

def _ids(env_key: str) -> List[int]:
    return _split_ids(os.getenv(env_key, ""))

def allowed_for(kind: str, channel_id: int) -> bool:
    kind = (kind or "").strip().lower()

    if kind == "qna":
        allow = set(_ids("QNA_CHANNEL_IDS"))
        single = os.getenv("QNA_CHANNEL_ID")
        if single:
            try:
                allow.add(int(single))
            except Exception:
                pass
        if not allow:
            log.warning("[chan-policy] QNA allowlist empty -> QNA disabled in all channels")
            return False
        return int(channel_id) in allow

    bl = set(_ids("XP_BLOCKLIST_CHANNEL_IDS"))
    al = set(_ids("XP_ALLOWLIST_CHANNEL_IDS"))
    if al:
        return int(channel_id) in al
    return int(channel_id) not in bl
