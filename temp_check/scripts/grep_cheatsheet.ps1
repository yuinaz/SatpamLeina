Param(
  [string]$LogPath = "/var/log/render.log"
)
Write-Host "[XP] signals (success):"
Select-String -Path $LogPath -Pattern "^\[?a08_xp_upstash_exact_keys_overlay|\[xp-state]|\[xp-upstash-sink]|Computed: |Wrote \(pipeline\):|export_xp_state" -SimpleMatch:$false -CaseSensitive:$false | ForEach-Object { $_.Line }

Write-Host "`n[XP] errors (should be empty):"
Select-String -Path $LogPath -Pattern "parse JSON failed|NoneType.*get\(|xp.*Traceback|xp.*error" -SimpleMatch:$false -CaseSensitive:$false | ForEach-Object { $_.Line }

Write-Host "`n[QNA] signals (autoask/autoreply):"
Select-String -Path $LogPath -Pattern "\[qna-autoask] channel=|Question by Leina|\[qna-autoreply]|\[auto-learn]" -SimpleMatch:$false -CaseSensitive:$false | ForEach-Object { $_.Line }

Write-Host "`n[QNA] errors (should be empty):"
Select-String -Path $LogPath -Pattern "qna.*Traceback|autolearn.*error|autolearn.*failed|qna.*failed" -SimpleMatch:$false -CaseSensitive:$false | ForEach-Object { $_.Line }
