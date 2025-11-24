$diff = git diff --cached
if ($diff -match '(GEMINI_API_KEY|GROQ_API_KEY|OPENAI_API_KEY|DISCORD_TOKEN|API_KEY|SECRET_KEY)') {
    Write-Host "✖ Commit diblokir: pola secret terdeteksi di staged changes." -ForegroundColor Red
    exit 1
}
$names = git diff --cached --name-only
foreach ($n in $names) {
    if ($n -match '(^|/)(\.env(\..*)?$|satpambot_config\.local\.json|config/.+\.local\.json)$') {
        Write-Host "✖ Commit diblokir: file rahasia lokal terdeteksi." -ForegroundColor Red
        exit 1
    }
}
exit 0
