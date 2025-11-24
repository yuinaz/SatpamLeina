import os, json
from pathlib import Path
def _state_path():
    here = Path(__file__).resolve()
    data_dir = here.parents[3] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "sticky_state.json"
def _load():
    p=_state_path()
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: return {}
    return {}
def _save(s): _state_path().write_text(json.dumps(s, indent=2))
async def upsert_sticky_embed(channel, embed, key='presence'):
    s=_load(); m=s.setdefault(str(channel.id),{}).get(key)
    try:
        if m:
            msg=await channel.fetch_message(int(m))
            if msg: await msg.edit(embed=embed, content=None)
            return msg
    except Exception: pass
    msg=await channel.send(embed=embed)
    s[str(channel.id)][key]=str(msg.id); _save(s); return msg

# ==== compat patch: upsert_sticky (only if missing) ====
try:
    _ = upsert_sticky  # type: ignore  # noqa: F821
except NameError:
    from typing import Optional

    async def upsert_sticky(
        channel,
        *,
        content: Optional[str] = None,
        embed=None,
        marker: str = "STICKY_PRESENCE",
        pin: bool = False,
        suppress: bool = False,
        history_limit: int = 25,
    ):
        """
        Upsert satu pesan 'sticky' per-channel.
        - Cari pesan bot terakhir yang memuat marker (di content atau embed.footer)
        - Jika ada -> edit
        - Jika tidak ada -> kirim baru
        """
        bot_user_id = None
        try:
            if getattr(channel, "guild", None) and getattr(channel.guild, "me", None):
                bot_user_id = channel.guild.me.id
            elif getattr(channel, "client", None) and getattr(channel.client, "user", None):
                bot_user_id = channel.client.user.id
        except Exception:
            pass

        sticky_msg = None
        try:
            async for m in channel.history(limit=history_limit):
                if bot_user_id is not None and getattr(m.author, "id", None) != bot_user_id:
                    continue
                ok = False
                try:
                    if m.content and marker in m.content:
                        ok = True
                    elif m.embeds:
                        try:
                            ft = getattr(m.embeds[0].footer, "text", "") if m.embeds else ""
                            if ft and marker in str(ft):
                                ok = True
                        except Exception:
                            pass
                except Exception:
                    pass
                if ok:
                    sticky_msg = m
                    break
        except Exception:
            # kalau tidak bisa akses history, kirim baru saja
            sticky_msg = None

        # siapkan content default supaya ada marker anti-duplikat
        final_content = content or ""
        if marker and (marker not in (final_content or "")):
            # taruh marker sebagai komentar tak kasat mata (zero-width space) biar aman
            suffix = f"\n<!-- {marker} -->"
            final_content = (final_content or "") + suffix

        if sticky_msg:
            try:
                await sticky_msg.edit(content=final_content or None, embed=embed, suppress=suppress)
                if pin:
                    try:
                        await sticky_msg.pin(reason="sticky")
                    except Exception:
                        pass
                return sticky_msg
            except Exception:
                pass  # jatuh ke kirim baru

        # kirim baru
        msg = await channel.send(content=final_content or None, embed=embed)
        if pin:
            try:
                await msg.pin(reason="sticky")
            except Exception:
                pass
        return msg
# ==== end compat patch ====
