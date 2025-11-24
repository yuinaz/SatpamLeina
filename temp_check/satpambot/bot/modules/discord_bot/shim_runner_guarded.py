# -*- coding: utf-8 -*-
from __future__ import annotations
import time, traceback, asyncio, logging
from importlib import import_module

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("shim_runner_guarded")

try:
    from satpambot.bot.selfheal.guardian import SelfHealGuardian
except Exception:
    SelfHealGuardian = None

def _find_entry_callable():
    try:
        base = import_module("satpambot.bot.modules.discord_bot.shim_runner")
    except Exception as e:
        LOG.error("cannot import base shim_runner: %r", e)
        return None
    for name in ("main", "run", "start", "run_main"):
        fn = getattr(base, name, None)
        if callable(fn):
            LOG.info("use base runner: %s.%s", base.__name__, name)
            return fn
    LOG.error("no callable entry found in %s", base.__name__)
    return None

def _guarded_loop(callable_main):
    if not callable(callable_main):
        LOG.error("callable_main is not callable"); return
    if not SelfHealGuardian:
        LOG.warning("SelfHealGuardian unavailable; running without guard")
        return callable_main()

    guard = SelfHealGuardian()
    while True:
        try:
            return callable_main()
        except SystemExit:
            raise
        except Exception as e:
            err_txt = "".join(traceback.format_exception_only(type(e), e)).strip()
            LOG.error("[selfheal] crash: %s", err_txt)
            ok, score, reason = asyncio.run(guard.approve_restart(err_txt))
            if not ok:
                LOG.error("[selfheal] restart VETO (score=%.2f): %s", score, reason)
                asyncio.run(asyncio.sleep(90))
                continue
            delay = guard.next_backoff()
            guard.record_crash()
            LOG.warning("[selfheal] restart APPROVED (score=%.2f). sleep %ss...", score, delay)
            asyncio.run(asyncio.sleep(delay))
def main():
    fn = _find_entry_callable()
    if fn is None:
        raise SystemExit(2)
    _guarded_loop(fn)

if __name__ == "__main__":
    main()
