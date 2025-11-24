try:
    from satpambot.bot.modules.discord_bot.cogs.qna_answer_award_xp_overlay import QnaAnswerAwardXPOverlay as _Orig
except Exception:
    try:
        from satpambot.bot.modules.discord_bot.cogs.qna_answer_award_xp_overlay import QnaAnswerAwardXP as _Orig
    except Exception:
        _Orig = None
def _cfg_str(k, d=""):
    try:
        from satpambot.bot.modules.discord_bot.cogs.qna_answer_award_xp_overlay import cfg_str
        return cfg_str(k, d)
    except Exception:
        import os; return os.getenv(k, d)
if _Orig:
    _orig_init = _Orig.__init__
    def _new_init(self, bot):
        _orig_init(self, bot)
        total_key = _cfg_str("XP_TOTAL_KEY", "")
        if total_key:
            try: self.senior_key = total_key
            except Exception: pass
    _Orig.__init__ = _new_init