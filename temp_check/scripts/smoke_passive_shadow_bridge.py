#!/usr/bin/env python3
import asyncio, os
from satpambot.bot.modules.discord_bot.cogs.a08f_passive_shadow_global_xp_overlay import PassiveShadowGlobalXPOverlay
from satpambot.bot.modules.discord_bot.helpers import xp_award

async def main():
    # monkey patch award to avoid network and verify HYBRID precedence
    called = {"sum":0}
    def fake(delta:int):
        called["sum"] += int(delta)
        return 123456, {"start_total": 1000, "required": 96500, "current": 5000}
    xp_award.award_xp_sync = fake

    # Set ENV only for behavior (no secrets)
    os.environ["PASSIVE_TO_BOT_ENABLE"] = "1"
    os.environ["PASSIVE_TO_BOT_SHARE"] = "1.0"
    os.environ["PASSIVE_TO_BOT_REASON_TOKENS"] = "passive,shadow,memory,normalize:chat,observer,passive-force-include"

    class Dummy: 
        async def add_cog(self, c): pass
        def dispatch(self, *a, **k): pass

    o = PassiveShadowGlobalXPOverlay(Dummy())
    # simulate events with various reasons
    await o.on_xp_add(1, 15, "passive_message")
    await o.on_xp_add(2, 15, "shadow_observer")
    await o.on_xp_add(3, 15, "normalize:chat:message")
    await o.on_xp_add(4, 15, "passive-force-include")
    print("[SMOKE] bridged delta:", called["sum"])  # expect 60

if __name__ == "__main__":
    asyncio.run(main())