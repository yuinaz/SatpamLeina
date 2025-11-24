from __future__ import annotations







import asyncio, io, gzip, json, datetime







from typing import Optional, Dict, Any, List







import discord















SNAPSHOT_PREFIX = "mlsnap_"







MAX_MESSAGES_SCAN = 250







MAX_ATTACH_PER_MSG = 2















CHAN_CANDIDATES = ["log-botphising","log-botphishing","log-satpam","log-satpam-bot"]







THREAD_PHISH = ["imagephising","image-phising","imagephishing","image-phishing"]







THREAD_WL = ["whitelist","white-list","wl-"]







THREAD_BANLOG = ["ban-log","log-ban","banlog"]







THREAD_BLACKLIST = ["blacklist","black-list"]







THREAD_STATE = ["ml-state"]















class CombinedState:







    def __init__(self):







        self.model_dict: Dict[str, Any] = {}







        self.whitelist = {"dhash64": [], "sha1k": []}







        self.exempt = {"threads": [], "channels": []}















    def to_json_bytes(self) -> bytes:







        data = {"version": 4, "model": self.model_dict, "whitelist": self.whitelist, "exempt": self.exempt}







        js = json.dumps(data).encode("utf-8")







        return gzip.compress(js)















    @classmethod







    def from_json_bytes(cls, b: bytes) -> "CombinedState":







        d = json.loads(gzip.decompress(b).decode("utf-8"))







        cs = cls()







        cs.model_dict = d.get("model", {})







        cs.whitelist = d.get("whitelist", {"dhash64": [], "sha1k": []})







        cs.exempt = d.get("exempt", {"threads": [], "channels": []})







        return cs















class MLState:







    def __init__(self, bot: discord.Client):







        self.bot = bot







        self.parent_channel_id: Optional[int] = None







        self.thread_id: Optional[int] = None







        self.combined = CombinedState()







        self.model = None  # OnlineNB















    def _name_has_any(self, name: str, keys: List[str]) -> bool:







        n = (name or "").lower()







        return any(k in n for k in keys)















    def find_log_channel(self) -> Optional[discord.TextChannel]:







        for ch in self.bot.get_all_channels():







            if isinstance(ch, discord.TextChannel):







                if self._name_has_any(ch.name, CHAN_CANDIDATES):







                    return ch







        return None















    def all_active_threads(self) -> List[discord.Thread]:







        ths = []







        for ch in self.bot.get_all_channels():







            if isinstance(ch, discord.TextChannel):







                try:







                    ths.extend(getattr(ch, "threads", []))







                except Exception:







                    pass







        return ths















    def classify_threads(self):







        phish = []







        wl = []







        banlog = []







        bl = []







        state = []







        for th in self.all_active_threads():







            n = (th.name or "").lower()







            if self._name_has_any(n, THREAD_STATE):







                state.append(th)







            if self._name_has_any(n, THREAD_PHISH):







                phish.append(th)







            if self._name_has_any(n, THREAD_WL):







                wl.append(th)







            if self._name_has_any(n, THREAD_BANLOG):







                banlog.append(th)







            if self._name_has_any(n, THREAD_BLACKLIST):







                bl.append(th)







        return phish, wl, banlog, bl, state















    async def _ensure_thread(self) -> Optional[discord.Thread]:







        parent = None







        if self.parent_channel_id:







            ch = self.bot.get_channel(self.parent_channel_id)







            if isinstance(ch, discord.TextChannel):







                parent = ch







        if parent is None:







            parent = self.find_log_channel()







        if parent is None:







            return None















        if self.thread_id:







            t = self.bot.get_channel(self.thread_id)







            if isinstance(t, discord.Thread):







                return t







        for th in getattr(parent, "threads", []):







            if (th.name or "").lower() == "ml-state":







                self.thread_id = th.id







                return th







        try:







            th = await parent.create_thread(name="ml-state", type=discord.ChannelType.public_thread)







            self.thread_id = th.id







            return th







        except Exception:







            return None















    async def load_latest(self) -> bool:







        from .online_nb import OnlineNB







        th = await self._ensure_thread()







        if th is None:







            self.model = OnlineNB()







            return False







        try:







            async for msg in th.history(limit=50, oldest_first=False):







                for a in msg.attachments:







                    if a.filename.startswith(SNAPSHOT_PREFIX) and a.filename.endswith(".json.gz"):







                        b = await a.read()







                        cs = CombinedState.from_json_bytes(b)







                        self.combined = cs







                        self.model = OnlineNB.from_dict(cs.model_dict) if cs.model_dict else OnlineNB()







                        return True







        except Exception:







            pass







        self.model = OnlineNB()







        return False















    async def save_snapshot(self) -> bool:







        if self.model is None:







            return False







        from .online_nb import OnlineNB







        self.combined.model_dict = self.model.to_dict()







        th = await self._ensure_thread()







        if th is None:







            return False







        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")







        fname = f"{SNAPSHOT_PREFIX}{ts}.json.gz"







        b = self.combined.to_json_bytes()







        file = discord.File(io.BytesIO(b), filename=fname)







        await th.send(content="ML combined snapshot", file=file)







        return True







