from __future__ import annotations
import datetime as dt
from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for

class WeeklyGate:
    def __init__(self):
        self.kv = get_kv_for("schedule")

    def should_run(self, name: str, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.utcnow()
        y, w, _ = now.isocalendar()
        this_week = f"{y}-W{w:02d}"
        key = f"weekly:{name}"
        doc = self.kv.get_json(key) or {}
        last = doc.get("value")
        return last != this_week

    def mark_ran(self, name: str, now: dt.datetime | None = None) -> None:
        now = now or dt.datetime.utcnow()
        y, w, _ = now.isocalendar()
        this_week = f"{y}-W{w:02d}"
        key = f"weekly:{name}"
        self.kv.set_json(key, {"value": this_week})
