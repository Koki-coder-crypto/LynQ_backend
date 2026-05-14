# Lynq Team Agent split-screen launcher
# Run in PowerShell: .\launch_team.ps1
# Or right-click → "Run with PowerShell"

param(
    [string]$Preset = "default",
    [string]$ApiKey = ""
)

$Script = Join-Path $PSScriptRoot "multi_agent_ui.py"

# Resolve API key
if ($ApiKey -eq "") {
    $ApiKey = $env:ANTHROPIC_API_KEY
}
if ($ApiKey -eq "" -or $null -eq $ApiKey) {
    Write-Host "ANTHROPIC_API_KEY not found." -ForegroundColor Yellow
    $ApiKey = Read-Host "Enter your API key (sk-ant-...)"
}
if ($ApiKey -eq "") {
    Write-Host "No API key provided. Exiting." -ForegroundColor Red
    exit 1
}

# Preset selection
if ($Preset -eq "default" -and $args.Count -eq 0) {
    Write-Host ""
    Write-Host "Select a preset:"
    Write-Host "  1. default  - Director(sonnet) + Coder(haiku) + Research(haiku)  [Pro recommended]"
    Write-Host "  2. dev      - Architect + Coder + Reviewer"
    Write-Host "  3. research - Finder + Analyst + Writer"
    Write-Host "  4. minimal  - 2 agents only (ultra-save)"
    Write-Host ""
    $choice = Read-Host "Number (Enter = 1)"
    switch ($choice) {
        "2" { $Preset = "dev" }
        "3" { $Preset = "research" }
        "4" { $Preset = "minimal" }
        default { $Preset = "default" }
    }
}

Write-Host ""
Write-Host "Launching: $Preset preset" -ForegroundColor Cyan

$env:ANTHROPIC_API_KEY = $ApiKey

# Check for Windows Terminal
$wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue

if ($wt) {
    Write-Host "Splitting screen in Windows Terminal..." -ForegroundColor Green
    Start-Process -FilePath "wt.exe" -ArgumentList @(
        "-w", "0",
        "sp", "-V",
        "--title", "Lynq Team [$Preset]",
        "--",
        "powershell", "-NoExit", "-Command",
        "`$env:ANTHROPIC_API_KEY='$ApiKey'; python '$Script' --preset $Preset"
    )
    Write-Host "Agent UI will open in the right pane." -ForegroundColor Green
} else {
    Write-Host "Launching in a new window..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList @(
        "/k",
        "set ANTHROPIC_API_KEY=$ApiKey && python `"$Script`" --preset $Preset"
    )
}
