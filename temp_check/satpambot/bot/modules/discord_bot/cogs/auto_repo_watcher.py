from __future__ import annotations

from discord.ext import commands

# auto_repo_watcher.py — best-stable (NO-ENV)
import asyncio, aiohttp, hashlib, io, json, os, sys, zipfile, time
from pathlib import Path
from typing import Dict, Any, List, Tuple

from satpambot.bot.modules.discord_bot.helpers import restart_guard as rg

BOOT_T0 = time.monotonic()
BOOT_COOLDOWN_S = 300.0      # 5m — jangan restart terlalu cepat abis deploy
FIRST_CHECK_DELAY_S = 120.0  # 2m — beri waktu instance lain settle
STATE_DIRS = ["/data/satpambot_state", "/tmp"]
def _state_path(name: str) -> Path:
    for d in STATE_DIRS:
        try:
            p = Path(d); p.mkdir(parents=True, exist_ok=True); return p / name
        except Exception: pass
    return Path("/tmp") / name
SHA_CACHE_FILE = _state_path("last_archive.sha256")

def _load_watch_cfg() -> Dict[str, Any]:
    p = Path("config") / "remote_watch.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"enabled": False, "interval_days": 4, "notify_thread_name": "log restart github"}

def _load_sync_cfg() -> Dict[str, Any]:
    p = Path("config") / "remote_sync.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"archive": "", "repo_root_prefix": "", "pull_sets": [
            {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
            {"include": ["satpambot/"], "allow_exts": ["py"]},
        ], "files": [], "timeout_s": 20}

async def _fetch_bytes(url: str, timeout: int) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            r.raise_for_status()
            return await r.read()

def _should_include(name: str, cfg: Dict[str, Any]) -> bool:
    pulls = cfg.get("pull_sets") or []
    name_l = name.lower()
    for rule in pulls:
        inc = rule.get("include") or []
        exts = [e.lower() for e in (rule.get("allow_exts") or [])]
        if inc and not any(name.startswith(i) for i in inc): continue
        if exts and not any(name_l.endswith("." + e) for e in exts): continue
        return True
    return False

def _apply_archive_bytes_if_changed(data: bytes, cfg: Dict[str, Any]) -> Tuple[List[str], int]:
    root_prefix = (cfg.get("repo_root_prefix") or "").strip()
    changed: List[str] = []; considered = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            name = info.filename
            rel = name[len(root_prefix):] if root_prefix and name.startswith(root_prefix) else name
            if not _should_include(rel, cfg): continue
            considered += 1
            target = Path(rel); target.parent.mkdir(parents=True, exist_ok=True)
            new_bytes = z.read(info)
            if target.exists():
                try:
                    old_bytes = target.read_bytes()
                    if old_bytes == new_bytes: continue  # skip identical
                except Exception: pass
            target.write_bytes(new_bytes); changed.append(rel)
    return changed, considered

async def _pull_archive_and_apply_if_changed() -> Tuple[List[str], str]:
    cfg = _load_sync_cfg()
    url = cfg.get("archive")
    if not url: return [], "no-archive-url"
    timeout = int(cfg.get("timeout_s", 20))
    data = await _fetch_bytes(url, timeout)
    sha = hashlib.sha256(data).hexdigest()
    if SHA_CACHE_FILE.exists():
        try:
            last = SHA_CACHE_FILE.read_text("utf-8").strip()
            if last == sha: return [], "same-zip"
        except Exception: pass
    changed, considered = _apply_archive_bytes_if_changed(data, cfg)
    try: SHA_CACHE_FILE.write_text(sha)
    except Exception: pass
    return changed, "applied" if changed else "no-diff"

def _reexec_inplace():
    os.execv(sys.executable, [sys.executable, *sys.argv])

class AutoRepoWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = asyncio.create_task(self._runner())

    async def _runner(self):
        cfg = _load_watch_cfg()
        if not cfg.get("enabled", False): return
        await asyncio.sleep(FIRST_CHECK_DELAY_S)  # biar rolling deploy selesai
        interval_s = max(1800.0, float(cfg.get("interval_days", 4)) * 86400.0)  # min 30m

        while True:
            try:
                changed, mode = await _pull_archive_and_apply_if_changed()
                if changed:
                    ok, age = rg.should_restart()
                    uptime = time.monotonic() - BOOT_T0
                    if ok and uptime >= BOOT_COOLDOWN_S:
                        rg.mark("watcher")
                        await asyncio.sleep(1.5)
                        _reexec_inplace()
                    # else: debounced — skip
            except Exception:
                pass
            await asyncio.sleep(interval_s)
async def setup(bot):
    await bot.add_cog(AutoRepoWatcher(bot))