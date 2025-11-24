from __future__ import annotations







import discord







from .state_store_discord import MLState







from .feature_extractor import extract_tokens, dhash64, sha1k















class GuardAdvisor:







    def __init__(self, bot: discord.Client):







        self.bot = bot







        self._state = MLState(bot)







        self._loaded = False















    async def _ensure_loaded(self):







        if not self._loaded:







            try:







                await self._state.load_latest()







            except Exception:







                pass







            self._loaded = True















    def is_exempt(self, message: discord.Message) -> bool:







        if isinstance(message.channel, discord.Thread):  # Global Thread Exempt







            return True







        ex = self._state.combined.exempt







        if message.channel.id in ex.get("channels", []):







            return True







        if isinstance(message.channel, discord.Thread) and message.channel.id in ex.get("threads", []):







            return True







        return False















    async def any_image_whitelisted_async(self, message: discord.Message) -> bool:







        await self._ensure_loaded()







        wl = self._state.combined.whitelist







        if not wl:







            return False







        for a in message.attachments[:







            3]:







            if a.content_type and a.content_type.startswith("image/"):







                try:







                    b = await a.read()







                except Exception:







                    continue







                h1 = dhash64(b)







                if h1 and h1 in set(wl.get("dhash64", [])):







                    return True







                if sha1k(b) in set(wl.get("sha1k", [])):







                    return True







        return False















    async def risk_score_from_content(self, message: discord.Message) -> float:







        await self._ensure_loaded()







        tokens = extract_tokens(message.content or "", None)







        if self._state.model is None:







            return 0.5







        return float(self._state.model.predict_proba(tokens)["phish"])







