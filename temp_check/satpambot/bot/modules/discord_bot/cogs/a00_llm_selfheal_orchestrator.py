# -*- coding: utf-8 -*-
"""
Self-heal orchestrator:
- Listens for errors.
- Summarizes the failure and asks LLM (Groq/Gemini via existing providers) for structured fixes.
- Applies edits locally (safe mode) OR via GitHub API (edit/commit on branch) depending on env.
- Can 'git pull' and optionally restart the process.

Environment flags (all optional):
  SELFHEAL_ENABLE=1                # enable actions (otherwise observe-only)
  SELFHEAL_MODE=git_local|github   # default: git_local
  SELFHEAL_REPO_DIR=/workspace/app # default: current working dir
  SELFHEAL_BRANCH=selfheal/auto    # target work branch (git_local)
  SELFHEAL_GH_REPO=owner/repo      # for github mode
  SELFHEAL_GH_BRANCH=selfheal/auto
  SELFHEAL_GITHUB_TOKEN=...        # PAT for GitHub API
  SELFHEAL_ALLOW_PULL=1            # allow git pull after editing
  SELFHEAL_ALLOW_RESTART=1         # allow process restart after pull
  SELFHEAL_QNA_CHANNEL_ID=...      # optional log target channel
"""
from discord.ext import commands
import os, json, logging, asyncio, traceback, pathlib, base64
from typing import Any, Dict, List, Optional, Tuple

import discord

from .a00_llm_provider_bootstrap import LLMProviderBootstrap  # ensure provider is loaded
from ..utils import selfheal_git as gitutil

LOG = logging.getLogger(__name__)

def _env(name: str, default: Optional[str]=None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v not in (None, "") else default

def _repo_dir() -> str:
    return _env("SELFHEAL_REPO_DIR", os.getcwd())

def _qna_channel_id() -> Optional[int]:
    v = _env("SELFHEAL_QNA_CHANNEL_ID") or _env("LEARNING_QNA_CHANNEL_ID")
    try: return int(v) if v else None
    except: return None

def _enabled() -> bool:
    return _env("SELFHEAL_ENABLE","0") == "1"

def _mode() -> str:
    return (_env("SELFHEAL_MODE","git_local") or "git_local").lower()

def _llm_model_label() -> str:
    prov = (_env("LLM_PROVIDER","auto") or "auto").lower()
    m1 = _env("LLM_GROQ_MODEL","llama-3.1-8b-instant")
    m2 = _env("LLM_GEMINI_MODEL","gemini-2.5-flash-lite")
    if prov == "groq": return f"Groq:{m1}"
    if prov == "gemini": return f"Gemini:{m2}"
    return f"AUTO(groq={m1}, gemini={m2})"

class LLMSelfHeal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ask_llm(self, summary: str) -> Optional[dict]:
        # Use bootstrapped llm_ask
        fn = getattr(self.bot, "llm_ask", None)
        if not fn:
            return None
        prompt = (
            "You are a code repair agent. Given an error log, propose minimal safe edits.\n"
            "Return STRICT JSON with keys:\n"
            "{\n"
            '  "edits": [\n'
            '    {"path": "<relative path from repo root>", "find": "<exact text to find>", "replace": "<replacement text>"}\n'
            "  ],\n"
            '  "explanation": "<short reason>"\n'
            "}\n"
            "Do NOT include markdown. Only valid JSON."
        )
        text = f"{prompt}\n\nERROR SUMMARY:\n{summary}"
        try:
            out = await fn(text, system="Keep changes minimal and safe; use exact string replacements.", temperature=0.1)
            # try parse json
            import json as _json
            start = out.find("{")
            end = out.rfind("}")
            js = out[start:end+1] if start!=-1 and end!=-1 else out
            return _json.loads(js)
        except Exception as e:
            LOG.warning("[selfheal] LLM parse failed: %r", e)
            return None

    def _apply_edits_local(self, repo_dir: str, edits: List[dict]) -> List[Tuple[str, bool, str]]:
        results = []
        for e in edits or []:
            p = pathlib.Path(repo_dir) / e.get("path","")
            try:
                s = p.read_text(encoding="utf-8")
                find = e.get("find","")
                rep  = e.get("replace","")
                if find not in s:
                    results.append((str(p), False, "pattern not found"))
                    continue
                s2 = s.replace(find, rep, 1)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(s2, encoding="utf-8")
                results.append((str(p), True, "edited"))
            except Exception as ex:
                results.append((str(p), False, f"edit failed: {ex}"))
        return results

    async def _maybe_restart(self):
        if _env("SELFHEAL_ALLOW_RESTART","0") != "1":
            return
        # On Render, exiting process usually triggers restart
        LOG.warning("[selfheal] restarting process as requested")
        os._exit(0)

    async def _do_selfheal(self, err_text: str):
        ch_id = _qna_channel_id()
        ch = self.bot.get_channel(ch_id) if ch_id else None
        if ch:
            try:
                await ch.send(f"🩹 SelfHeal invoked. Provider={_llm_model_label()}")
            except Exception: pass

        plan = await self._ask_llm(err_text[:4000])
        if not plan or not isinstance(plan, dict):
            LOG.warning("[selfheal] no plan from LLM")
            return
        edits = plan.get("edits") or []
        repo_dir = _repo_dir()
        mode = _mode()

        if mode == "git_local":
            # local apply + branch + push (optional)
            branch = _env("SELFHEAL_BRANCH","selfheal/auto")
            gitutil.ensure_user(repo_dir)
            gitutil.checkout_branch(repo_dir, branch)
            results = self._apply_edits_local(repo_dir, edits)
            msg = "Selfheal: apply edits\n" + json.dumps(results, ensure_ascii=False)
            gitutil.add_commit_push(repo_dir, msg, branch=branch)
            if _env("SELFHEAL_ALLOW_PULL","0") == "1":
                gitutil.pull(repo_dir, branch=branch)
        else:
            # github mode: update file contents via API
            gh_repo = _env("SELFHEAL_GH_REPO")
            gh_branch = _env("SELFHEAL_GH_BRANCH","selfheal/auto")
            token = _env("SELFHEAL_GITHUB_TOKEN")
            if not (gh_repo and token):
                LOG.warning("[selfheal] github mode requested but token/repo missing")
                return
            for e in edits:
                path = e.get("path","")
                full = os.path.join(repo_dir, path)
                try:
                    cur = ""
                    try:
                        cur = open(full,"r",encoding="utf-8").read()
                    except Exception:
                        pass
                    find = e.get("find",""); rep = e.get("replace","")
                    if cur and find in cur:
                        new = cur.replace(find, rep, 1)
                    else:
                        new = rep  # create new content if not exist
                    gitutil.gh_update_file(gh_repo, path, new.encode("utf-8"), "Selfheal: apply edit", gh_branch, token)
                except Exception as ex:
                    LOG.warning("[selfheal] gh update failed for %s: %r", path, ex)

        if ch:
            try:
                await ch.send(f"🩹 SelfHeal applied. Plan: ```json\n{json.dumps(plan)[:1900]}\n```")
            except Exception: pass

        await self._maybe_restart()

    # ---- Discord event hooks ----
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not _enabled(): return
        summary = f"{type(error).__name__}: {error}\n\n{traceback.format_exc()[-2000:]}"
        await self._do_selfheal(summary)

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        if not _enabled(): return
        tb = traceback.format_exc()
        summary = f"event={event_method}\n\n{tb[-2000:]}"
        await self._do_selfheal(summary)
async def setup(bot):
    await bot.add_cog(LLMSelfHeal(bot))