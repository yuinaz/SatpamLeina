#!/usr/bin/env python3
"""
Neuro Smoketest Suite (v6 — single namespace, no alt 'modules.*')
- Auto-path detection
- Rich 'discord' stub
- Gate policy simulation
- Works even if an asyncio loop is already running (Jupyter/IDE)
"""
import os, sys, json, importlib, glob, types, asyncio
from threading import Thread as _Thread
from typing import cast, Any

def env(k, d=None): return os.getenv(k, d)
def ok(m): print("[OK]", m)
def warn(m): print("[WARN]", m)

def _maybe_add_path(p):
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

def locate_project_root():
    hint = env("NEURO_SMOKE_PATH_HINT")
    if hint and os.path.isdir(hint):
        _maybe_add_path(hint); return hint
    base = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.abspath(os.path.join(base, ".."))
    if os.path.isdir(os.path.join(cand, "satpambot")):
        _maybe_add_path(cand); return cand
    cur = os.getcwd()
    for up in [cur, os.path.dirname(cur), os.path.dirname(os.path.dirname(cur)), os.path.dirname(os.path.dirname(os.path.dirname(cur))) ]:
        if os.path.isdir(os.path.join(up, "satpambot")):
            _maybe_add_path(up); return up
    for up in [cur, os.path.dirname(cur)]:
        hits = glob.glob(os.path.join(up, "**", "satpambot"), recursive=True)
        for h in hits:
            root = os.path.dirname(h)
            _maybe_add_path(root); return root
    return None

def run_coro(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # already running: run in a dedicated thread + loop
    result = {}
    def _runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["value"] = loop.run_until_complete(coro)
        finally:
            loop.close()
    t = _Thread(target=_runner, daemon=True)
    t.start(); t.join()
    return result.get("value")

def install_discord_stub():
    try:
        import discord  # noqa
        ok("discord module present")
        return
    except Exception:
        pass
    discord = types.ModuleType("discord")
    abc = types.ModuleType("discord.abc")
    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")
    class Cog:
        @classmethod
        def listener(cls, *a, **kw):
            def deco(f): return f
            return deco
    def _decorator(*dargs, **dkwargs):
        def wrap(f): return f
        return wrap
    class _Group:
        def __init__(self, f): self.func = f
        def __call__(self, *a, **kw): 
            return self.func(*a, **kw)
        def command(self, *a, **kw):
            def deco(f): return f
            return deco
        def group(self, *a, **kw):
            def deco(f): return _Group(f)
            return deco
    # assign attributes dynamically; cast modules to Any to satisfy static checkers
    c_mod = cast(Any, commands)
    c_mod.Cog = Cog
    c_mod.command = _decorator
    c_mod.group = lambda *a, **kw: (lambda f: _Group(f))
    c_mod.has_permissions = _decorator
    c_mod.bot_has_permissions = _decorator
    d_mod = cast(Any, discord)
    d_mod.abc = abc
    d_mod.ext = ext
    e_mod = cast(Any, ext)
    e_mod.commands = commands
    sys.modules["discord"] = discord
    sys.modules["discord.abc"] = abc
    sys.modules["discord.ext"] = ext
    sys.modules["discord.ext.commands"] = commands
    warn("discord stubbed for import-only")

def try_import(name):
    try:
        return importlib.import_module(name)
    except Exception as e:
        warn(f"import {name} skipped: {e}")
        return None

def check_envs():
    if env("GEMINI_API_KEY"): ok("GEMINI_API_KEY detected")
    else: warn("GEMINI_API_KEY missing")
    if env("GROQ_API_KEY"): ok("GROQ_API_KEY detected")
    else: warn("GROQ_API_KEY missing")

def import_sanity():
    roots = ["satpambot.bot.modules.discord_bot.cogs"]
    names = [
        "a00_governor_gate_neurosama_overlay",
        "a24_autolearn_qna_autoreply_fix_overlay",
        "a06_persona_unified_provider_overlay",
    ]
    seen = 0
    for r in roots:
        for n in names:
            mod = try_import(f"{r}.{n}")
            if mod: seen += 1
    if seen == 0:
        warn("No overlay modules imported (path/namespace?).")
    else:
        ok(f"Imported overlays: {seen}")
    return seen

def simulate_gate():
    G = try_import("satpambot.bot.modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay")
    if not G:
        warn("simulate_gate skipped (overlay not importable)")
        return
    class DummyUS:
        store = {}
        async def get(self, k): return self.store.get(k)
        async def set(self, k, v): self.store[k]=str(v); return True
    class DummyBot: pass
    try:
        cog = G.GovernorGate(DummyBot())
    except Exception as e:
        warn(f"simulate_gate construct failed: {e}")
        return
    cog.us = DummyUS()
    import json as _json
    learn = int(env("LEARN_CHANNEL_ID","1426571542627614772"))
    public = int(env("PUBLIC_CHANNEL_ID","886534544688308265"))
    # Locked
    cog.us.store = {"governor:gate_locked":"1","governor:public_channels_json":_json.dumps([public])}
    a = run_coro(cog._send_guard(learn,"q: hi"))
    b = run_coro(cog._send_guard(public,"q: hi"))
    print("locked:", a, b); ok("locked policy OK" if a and not b else "locked policy FAIL")
    # Unlocked
    cog.us.store = {"governor:gate_locked":"0","governor:public_channels_json":_json.dumps([public])}
    a = run_coro(cog._send_guard(learn,"q: hi"))
    b = run_coro(cog._send_guard(public,"q: hi"))
    print("unlocked:", a, b); ok("unlocked policy OK" if a and b else "unlocked policy FAIL")

def main():
    root = locate_project_root()
    print(f"[path] project_root={root}")
    install_discord_stub()
    check_envs()
    import_sanity()
    simulate_gate()
    print("done.")
if __name__ == "__main__":
    main()
