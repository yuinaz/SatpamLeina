
from discord.ext import commands
import os
import re
import io
import json
from typing import Dict, Any, Iterable, Tuple, List, Optional

import aiohttp
import discord

from discord import app_commands, Embed, Colour, File

DASHBOARD_BASE = os.getenv("SATPAMBOT_DASHBOARD_URL", "http://127.0.0.1:10000").rstrip("/")
API_PHASH = f"{DASHBOARD_BASE}/api/phish/phash"
API_UICFG = f"{DASHBOARD_BASE}/api/ui-config"

URL_RX = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
DOMAIN_RX = re.compile(r"^(?:https?://)?([^/\s:]+)", re.IGNORECASE)
INVITE_DOMAINS = {"discord.gg","discord.com","discordapp.com"}

def _safe_len(x) -> int:
    try:
        return len(x)
    except Exception:
        return 0

def _maybe_iter(x) -> Iterable:
    if x is None:
        return []
    if isinstance(x, dict):
        return list(x.keys())
    try:
        iter(x)
        return x
    except Exception:
        return []

def _classify_name(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["whitelist","white_list","allowlist","allow_list","allow"]):
        return "wl"
    if any(k in n for k in ["blacklist","black_list","blocklist","block_list","denylist","deny_list","deny","black"]):
        return "bl"
    return "other"

def _discover_lists(bot: commands.Bot) -> Dict[str, Tuple[str, Iterable, str]]:
    candidates = [
        "whitelist","white_list","domain_whitelist","url_whitelist","invite_whitelist","allowlist","allow_list","allow_domains",
        "blacklist","black_list","domain_blacklist","url_blacklist","blocklist","invite_blacklist","denylist","deny_list","deny_domains"
    ]
    found: Dict[str, Tuple[str, Iterable, str]] = {}
    for cname, cog in bot.cogs.items():
        for attr in candidates:
            try:
                if hasattr(cog, attr):
                    val = getattr(cog, attr)
                    if val is None:
                        continue
                    it = _maybe_iter(val)
                    k = f"{cname}.{attr}"
                    found[k] = (k, it, _classify_name(k))
            except Exception:
                continue
    return found

async def _fetch_json(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                try:
                    return await resp.json()
                except Exception:
                    return {}
    except Exception:
        return {}
    return {}

class GuardDiag(commands.Cog):
    """Ephemeral diagnostic slash-commands: /guard status, /guard test, /guard list."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    guard = app_commands.Group(name="guard", description="Diagnostik whitelist/blacklist & pHash (ephemeral).")

    @guard.command(name="status", description="Ringkasan status guard (autoban, pHash count, wl/bl counts).")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            async with aiohttp.ClientSession() as session:
                phash = await _fetch_json(session, API_PHASH)
                ui = await _fetch_json(session, API_UICFG)
        except Exception:
            phash, ui = {}, {}
        count = phash.get("count")
        if count is None and isinstance(phash.get("phash"), list):
            count = len(phash["phash"])
        autoban = ui.get("autoban")
        lists = _discover_lists(self.bot)
        wl = [(k,_safe_len(v)) for k,(qn,v,kind) in lists.items() if kind == "wl"]
        bl = [(k,_safe_len(v)) for k,(qn,v,kind) in lists.items() if kind == "bl"]

        wl.sort(key=lambda x: x[1], reverse=True)
        bl.sort(key=lambda x: x[1], reverse=True)

        emb = Embed(
            title="Guard status",
            description="Ringkasan konfigurasi yang terdeteksi.",
            colour=Colour.blurple(),
        )
        emb.add_field(name="Autoban", value=str(autoban) if autoban is not None else "Unknown", inline=True)
        emb.add_field(name="pHash count", value=str(count) if count is not None else "Unknown", inline=True)
        if wl:
            wl_txt = "\n".join(f"• `{name}`: **{n}**" for name,n in wl[:10])
            emb.add_field(name="Whitelist (top)", value=wl_txt, inline=False)
        if bl:
            bl_txt = "\n".join(f"• `{name}`: **{n}**" for name,n in bl[:10])
            emb.add_field(name="Blacklist (top)", value=bl_txt, inline=False)
        emb.set_footer(text="Ephemeral • hanya terlihat oleh kamu")
        await interaction.followup.send(embed=emb, ephemeral=True)

    @guard.command(name="test", description="Dry-run: uji sebuah teks/URL terhadap rule whitelist/blacklist.")
    @app_commands.describe(teks="Teks atau URL yang ingin diuji")
    async def test(self, interaction: discord.Interaction, teks: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        original = teks.strip()
        m = DOMAIN_RX.search(original)
        domain = m.group(1).lower() if m else None
        is_invite = False
        if domain:
            for d in INVITE_DOMAINS:
                if domain.endswith(d):
                    is_invite = True
                    break

        lists = _discover_lists(self.bot)
        hits = []
        decision = "NEUTRAL"

        def _contains(container, item):
            try:
                if isinstance(container, dict):
                    return item in container or item in container.keys()
                return item in container
            except Exception:
                return False

        for key,(qn,it,kind) in lists.items():
            for probe in filter(None, [original, domain]):
                try:
                    if _contains(it, probe):
                        hits.append((key, probe, kind))
                except Exception:
                    continue

        wl_hit = [h for h in hits if h[2] == "wl"]
        bl_hit = [h for h in hits if h[2] == "bl"]
        if wl_hit and not bl_hit:
            decision = "ALLOW (whitelist)"
        elif bl_hit and not wl_hit:
            decision = "BLOCK (blacklist)"
        elif bl_hit and wl_hit:
            decision = "ALLOW (whitelist overrides), but blacklist match exists"

        emb = Embed(
            title="Guard dry‑run",
            description="Hasil uji aturan tanpa tindakan.",
            colour=Colour.green() if decision.startswith("ALLOW") else (Colour.red() if decision.startswith("BLOCK") else Colour.gold())
        )
        emb.add_field(name="Input", value=f"`{original}`", inline=False)
        if domain:
            emb.add_field(name="Domain", value=f"`{domain}`", inline=True)
        if is_invite:
            emb.add_field(name="Tipe", value="Discord Invite", inline=True)
        if hits:
            lines = "\n".join(f"• `{src}` ⟵ `{probe}` ({kind})" for src, probe, kind in hits[:20])
            emb.add_field(name="Matches", value=lines, inline=False)
        else:
            emb.add_field(name="Matches", value="(tidak ada)", inline=False)
        emb.add_field(name="Decision", value=decision, inline=False)
        emb.set_footer(text="Ephemeral • hanya terlihat oleh kamu")
        await interaction.followup.send(embed=emb, ephemeral=True)

    @guard.command(name="list", description="Lihat isi whitelist/blacklist secara ephemeral (paging & export).")
    @app_commands.describe(
        tipe="Pilih daftar: whitelist / blacklist / both",
        source="Sumber (nama.cog.attr). Kosongkan untuk otomatis pilih yang terbesar.",
        page="Halaman (mulai dari 1)",
        limit="Jumlah item per halaman (5–50)",
        export="Lampirkan file JSON semua item (bukan hanya halaman)"
    )
    @app_commands.choices(
        tipe=[
            app_commands.Choice(name="whitelist", value="wl"),
            app_commands.Choice(name="blacklist", value="bl"),
            app_commands.Choice(name="both", value="both"),
        ]
    )
    async def list_cmd(
        self,
        interaction: discord.Interaction,
        tipe: app_commands.Choice[str],
        source: Optional[str] = None,
        page: Optional[int] = 1,
        limit: Optional[int] = 20,
        export: Optional[bool] = False,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        limit = max(5, min(50, int(limit or 20)))
        page = max(1, int(page or 1))

        lists = _discover_lists(self.bot)
        def _ok(kind):
            if tipe.value == "both":
                return kind in ("wl","bl")
            return kind == tipe.value

        filtered = {k:(qn,it,kind) for k,(qn,it,kind) in lists.items() if _ok(kind)}
        if not filtered:
            await interaction.followup.send(f"Tidak menemukan daftar untuk tipe `{tipe.name}`.", ephemeral=True)
            return

        if source:
            s = source.lower()
            sel_key = None
            for k in filtered.keys():
                if s in k.lower():
                    sel_key = k
                    break
            if sel_key is None:
                await interaction.followup.send(f"Sumber `{source}` tidak ditemukan untuk tipe `{tipe.name}`.", ephemeral=True)
                return
        else:
            sel_key = max(filtered.keys(), key=lambda k: _safe_len(filtered[k][1]))
        qualname, iterable, kind = filtered[sel_key]
        items = list(_maybe_iter(iterable))

        total = len(items)
        total_pages = max(1, (total + limit - 1) // limit)
        page = min(page, total_pages)
        start = (page - 1) * limit
        end = min(start + limit, total)
        page_items = items[start:end]

        emb = Embed(
            title=f"Guard list — {'Whitelist' if kind=='wl' else 'Blacklist'}",
            description=f"Sumber: `{qualname}`",
            colour=Colour.green() if kind == 'wl' else Colour.red()
        )
        emb.add_field(name="Count", value=str(total), inline=True)
        emb.add_field(name="Page", value=f"{page}/{total_pages}", inline=True)

        if page_items:
            block = "\n".join(str(x) for x in page_items)
            if len(block) > 1000:
                block = block[:1000] + "\n…"
            emb.add_field(name="Items", value=f"```\n{block}\n```", inline=False)
        else:
            emb.add_field(name="Items", value="(halaman kosong)", inline=False)
        emb.set_footer(text="Ephemeral • hanya terlihat oleh kamu")

        files = None
        if export and items:
            try:
                buf = io.BytesIO(json.dumps({"source": qualname, "kind": kind, "items": items}, ensure_ascii=False, indent=2).encode("utf-8"))
                files = [File(fp=buf, filename=f"{kind}_{qualname.replace('.', '_')}.json")]
            except Exception:
                files = None

        await interaction.followup.send(embed=emb, files=files, ephemeral=True)

    @list_cmd.autocomplete("source")
    async def source_autocomplete(self, interaction: discord.Interaction, current: str):
        lists = _discover_lists(self.bot)
        chosen = None
        for opt in interaction.data.get("options", []):
            if opt.get("name") == "tipe":
                chosen = opt.get("value")
        def _ok(kind):
            if chosen in (None, "both"):
                return kind in ("wl","bl")
            return kind == chosen
        keys = [k for k,(qn,it,kind) in lists.items() if _ok(kind)]
        current_lower = (current or "").lower()
        if current_lower:
            keys = [k for k in keys if current_lower in k.lower()]
        keys.sort()
        return [app_commands.Choice(name=k[:100], value=k) for k in keys[:25]]
async def setup(bot: commands.Bot):
    await bot.add_cog(GuardDiag(bot))
def legacy_setup(bot: commands.Bot):
    bot.add_cog(GuardDiag(bot))