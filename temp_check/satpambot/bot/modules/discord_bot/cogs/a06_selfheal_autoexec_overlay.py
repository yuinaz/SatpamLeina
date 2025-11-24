
# a06_selfheal_autoexec_overlay.py (v7.4)
from discord.ext import commands
import os, re, json, asyncio, logging, shlex, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
def _env(k, default=None):
    v = os.getenv(k, default)
    if isinstance(v, str): return v.strip()
    return v
try: REPO_DIR = Path(_env("CWD", "/opt/render/project/src"))
except Exception: REPO_DIR = Path("/opt/render/project/src")
GITHUB_REPO = _env("GITHUB_REPO"); GITHUB_BRANCH = _env("GITHUB_BRANCH","main"); GITHUB_TOKEN = _env("GITHUB_TOKEN")
USE_GIT = _env("SELFHEAL_USE_GIT","1") == "1"
def _extract_edits(text: str) -> Optional[Dict[str,Any]]:
    try:
        m = re.search(r"\{(?:.|\n)*\}", text); cand=None
        if m:
            try: cand=json.loads(m.group(0))
            except Exception: cand=None
        if isinstance(cand, dict) and "edits" in cand: return cand
        path_m = re.search(r"path\s*=\s*([^\n`]+)", text)
        code_m = re.search(r"```(?:python|py|)([\s\S]*?)```", text)
        if path_m and code_m: return {"edits":[{"path":path_m.group(1).strip(),"type":"replace","content":code_m.group(1)}]}
    except Exception: return None
    return None
def _apply_edits(edits: Dict[str,Any]) -> List[str]:
    changed=[]
    try:
        for e in edits.get("edits", []):
            p = REPO_DIR / e.get("path","").strip("/"); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(e.get("content","")), encoding="utf-8"); changed.append(str(p))
    except Exception as e: logger.info("[selfheal] apply edits failed: %r", e)
    return changed
def _git_push(changed_files: List[str]) -> bool:
    if not USE_GIT: return False
    try:
        def run(cmd): logger.info("[selfheal:git] %s", cmd); return subprocess.run(shlex.split(cmd), cwd=str(REPO_DIR), capture_output=True, text=True)
        run("git config user.email bot@localhost"); run("git config user.name SelfHealBot")
        run(f"git checkout -B {GITHUB_BRANCH}"); run("git add -A"); run("bash -lc 'git commit -m selfheal:auto-fix || true'")
        if GITHUB_TOKEN and GITHUB_REPO:
            remote=f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"; res=run(f"git push {remote} HEAD:{GITHUB_BRANCH}"); return res.returncode==0
        res=run(f"git push origin HEAD:{GITHUB_BRANCH}"); return res.returncode==0
    except Exception as e: logger.info("[selfheal:git] push failed: %r", e); return False
async def _restart_via_existing_cogs(bot) -> bool:
    for cog_name in ("repo_pull_and_restart","repo_restart_hook","repo_restart","repo_pull"):
        cog = bot.get_cog(cog_name)
        if not cog: continue
        for m in ("pull_and_restart","restart","pullrepo","pull_and_reboot","pull","do_restart"):
            fn = getattr(cog, m, None)
            if fn:
                try: res = fn(); 
                except Exception as e: logger.info("[selfheal:restart] %s.%s call error: %r", cog_name, m, e); continue
                try: 
                    import asyncio
                    if asyncio.iscoroutine(res): await res
                    logger.info("[selfheal:restart] used %s.%s()", cog_name, m); return True
                except Exception as e: logger.info("[selfheal:restart] %s.%s failed: %r", cog_name, m, e)
    return False
def _restart_local_process():
    try: subprocess.run(["git","pull"], cwd=str(REPO_DIR), capture_output=True, text=True)
    except Exception: pass
    logger.info("[selfheal:restart] exiting process for restart"); os._exit(0)
async def _llm_fix(bot, prompt: str) -> Tuple[bool,str]:
    ask = getattr(bot, "llm_ask", None)
    if not ask: return (False, "llm-provider-not-ready")
    text = await ask(prompt, system="You fix Python Discord bot modules. Return JSON with file edits.", temperature=0.2)
    if not text: return (False,"no-llm-response")
    edits = _extract_edits(text); 
    if not edits: return (False,"no-edits-parsed")
    changed=_apply_edits(edits); 
    if not changed: return (False,"no-files-changed")
    pushed=_git_push(changed); used=await _restart_via_existing_cogs(bot)
    if not used: _restart_local_process()
    return (True, f"changed={len(changed)} pushed={pushed} restart={'cog' if used else 'process'}")
class SelfHealAutoExec(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.busy=False
    async def _handle_error(self, text: str):
        if self.busy: return
        self.busy=True
        try:
            prefix="Make minimal edits to eliminate error/warnings. Return JSON {\"edits\":[{\"path\":\"...\",\"type\":\"replace\",\"content\":\"...\"}]}\n"
            ok, info = await _llm_fix(self.bot, prefix + text[:4000])
            logger.info("[selfheal:autoexec] result: %s (%s)", ok, info)
        finally: self.busy=False
    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        try: await self._handle_error(f"on_error({event_method}): args={str(args)[:400]} kwargs={str(kwargs)[:400]}")
        except Exception as e: logger.info("[selfheal:autoexec] on_error failed: %r", e)
    @commands.Cog.listener()
    async def on_exception(self, *args, **kwargs):
        try: await self._handle_error(f"exception: {args} {kwargs}")
        except Exception as e: logger.info("[selfheal:autoexec] on_exception failed: %r", e)
async def setup(bot):
    try: await bot.add_cog(SelfHealAutoExec(bot))
    except Exception as e: logger.info("[selfheal:autoexec] setup swallowed: %r", e)