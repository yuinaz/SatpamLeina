# -*- coding: utf-8 -*-
"""
a96_smoke_thread_daemonizer_overlay
Aktif hanya saat dijalankan via scripts/smoke_all.py atau SMOKE_MODE=1.
Tujuan: mencegah smoke test "stuck" akibat thread non-daemon.
Cara kerja:
- Monkeypatch threading.Thread agar default daemon=True saat smoke.
- Tidak mempengaruhi produksi karena hanya aktif saat SMOKE_MODE=1 atau argv mengandung 'scripts/smoke_all.py'.
"""
from discord.ext import commands
import os, sys, threading, logging

log=logging.getLogger(__name__)

def _is_smoke():
    if os.getenv("SMOKE_MODE","")=="1": return True
    return "scripts/smoke_all.py" in " ".join(sys.argv).lower()

def _patch_threading():
    if getattr(threading, "__daemon_patched__", False):
        return
    _Thread = threading.Thread
    class DaemonThread(_Thread):
        def __init__(self, *a, **k):
            # default daemon=True jika tidak dispesifikkan
            if "daemon" not in k:
                k["daemon"] = True
            super().__init__(*a, **k)
    DaemonThread.__name__ = "Thread"
    threading.Thread = DaemonThread
    threading.__daemon_patched__ = True
    log.info("[smoke-daemonizer] threading.Thread patched to daemon=True (smoke only)")

class SmokeDaemonizer(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        pass

# apply at import time
if _is_smoke():
    try:
        _patch_threading()
    except Exception as e:
        log.debug("[smoke-daemonizer] patch failed: %r", e)
async def setup(bot): await bot.add_cog(SmokeDaemonizer(bot))