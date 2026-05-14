# Claude チームエージェント分割画面起動スクリプト
# PowerShell で実行: .\launch_team.ps1
# または右クリック → "PowerShell で実行"

param(
    [string]$Preset = "default",
    [string]$ApiKey = ""
)

$Script = Join-Path $PSScriptRoot "multi_agent_ui.py"

# API キー取得
if ($ApiKey -eq "") {
    $ApiKey = $env:ANTHROPIC_API_KEY
}
if ($ApiKey -eq "" -or $null -eq $ApiKey) {
    Write-Host "ANTHROPIC_API_KEY が見つかりません。" -ForegroundColor Yellow
    $ApiKey = Read-Host "API キーを入力してください (sk-ant-...)"
}
if ($ApiKey -eq "") {
    Write-Host "API キーが入力されていません。終了します。" -ForegroundColor Red
    exit 1
}

# プリセット選択
if ($Preset -eq "default" -and $args.Count -eq 0) {
    Write-Host ""
    Write-Host "プリセットを選択:"
    Write-Host "  1. default  - Director(sonnet) + Coder(haiku) + Research(haiku)  [Pro推奨]"
    Write-Host "  2. dev      - Architect + Coder + Reviewer"
    Write-Host "  3. research - Finder + Analyst + Writer"
    Write-Host "  4. minimal  - 2体のみ（超節約）"
    Write-Host ""
    $choice = Read-Host "番号 (Enter = 1)"
    switch ($choice) {
        "2" { $Preset = "dev" }
        "3" { $Preset = "research" }
        "4" { $Preset = "minimal" }
        default { $Preset = "default" }
    }
}

Write-Host ""
Write-Host "起動: $Preset プリセット" -ForegroundColor Cyan

# 環境変数をセットしてエージェント起動
$env:ANTHROPIC_API_KEY = $ApiKey

# Windows Terminal が使えるか確認
$wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue

if ($wt) {
    # 現在のウィンドウを縦分割して右ペインでTUI起動
    Write-Host "Windows Terminal で画面を分割します..." -ForegroundColor Green
    $envBlock = "ANTHROPIC_API_KEY=$ApiKey"
    Start-Process -FilePath "wt.exe" -ArgumentList @(
        "-w", "0",
        "sp", "-V",
        "--title", "Claude Team [$Preset]",
        "--",
        "powershell", "-NoExit", "-Command",
        "`$env:ANTHROPIC_API_KEY='$ApiKey'; python '$Script' --preset $Preset"
    )
    Write-Host "右ペインにエージェント画面が開きます。" -ForegroundColor Green
} else {
    # Windows Terminal がない場合は新しいcmdウィンドウで起動
    Write-Host "新しいウィンドウで起動します..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList @(
        "/k",
        "set ANTHROPIC_API_KEY=$ApiKey && python `"$Script`" --preset $Preset"
    )
}
