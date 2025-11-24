# Verify after applying patch

1. Deploy/copy patched files over your repo.
2. Ensure env/json:
   - `LEARNING_MIN_LABEL="KULIAH-S6"`
   - `LADDER_AUTOSEED=0` (default) unless you want it
   - `XP_FORCE_RESET_ON_BOOT=0` (default)
3. Start the bot. Wait ~90s for `learning-repair-once`.
4. Check keys:
```
AUTH="Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"
BASE="$UPSTASH_REDIS_REST_URL"
for k in learning:status learning:status_json xp:bot:senior_total; do
  echo -n "$k -> "; curl -s -H "$AUTH" "$BASE/get/$k"; echo
done
```
Should be KULIAH-S6 and correct totals.
5. Confirm no blocking requests in async loops and no ladder autoseed timeouts.
