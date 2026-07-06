# FA bootstrap -- Windows
# Run from FA folder:  .\bootstrap\setup.ps1
# Idempotent -- safe to re-run.

$ErrorActionPreference = 'Stop'
$FA_ROOT = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=== FA Bootstrap (Windows) ===" -ForegroundColor Cyan
Write-Host "FA root: $FA_ROOT"
Write-Host ""

$allGood = $true

# --- 1. Python 3.12+ ---
Write-Host "[1/5] Checking Python 3.12+..."
$pyCmd = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $v = & $candidate --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $v -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 12) {
            $pyCmd = $candidate
            Write-Host "  OK: $v via '$candidate'" -ForegroundColor Green
            break
        }
    }
}
if (-not $pyCmd) {
    Write-Host "  MISSING: Python 3.12+ not found" -ForegroundColor Red
    Write-Host "  -> Install from https://www.python.org/downloads/ (tick 'Add to PATH')"
    Write-Host "  -> Or: winget install Python.Python.3.12"
    $allGood = $false
}

# --- 2. uv (auto-install if missing) ---
Write-Host "[2/5] Checking uv (Python package manager)..."
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvVer = & uv --version 2>&1
    Write-Host "  OK: $uvVer" -ForegroundColor Green
} else {
    Write-Host "  MISSING: auto-installing uv..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Host "  Installed. You may need to restart the shell to pick up PATH." -ForegroundColor Green
        } else {
            Write-Host "  Installed but not on PATH yet. Restart terminal and re-run this script." -ForegroundColor Yellow
            $allGood = $false
        }
    } catch {
        Write-Host "  FAILED auto-install. Install manually: https://astral.sh/uv" -ForegroundColor Red
        $allGood = $false
    }
}

# --- 3. Claude Code ---
Write-Host "[3/5] Checking Claude Code..."
$ccCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($ccCmd) {
    Write-Host "  OK: $(& claude --version 2>&1)" -ForegroundColor Green
} else {
    Write-Host "  NOT FOUND in PATH (may still work via IDE extension)" -ForegroundColor Yellow
    Write-Host "  -> Install: https://claude.com/claude-code"
    # Don't fail -- Claude Code may be installed as VSCode extension
}

# --- 4. Portfolio config + MCP server ---
Write-Host "[4/5] Portfolio config + MCP server..."
$holdings = Join-Path $FA_ROOT "portfolio\holdings.json"
$sample = Join-Path $FA_ROOT "portfolio\holdings.sample.json"
if (-not (Test-Path $holdings)) {
    if (Test-Path $sample) {
        Copy-Item $sample $holdings
        Write-Host "  OK: created portfolio\holdings.json from sample (edit it with your own accounts)" -ForegroundColor Green
    } else {
        Write-Host "  NOTE: portfolio\holdings.sample.json missing; add your own portfolio\holdings.json" -ForegroundColor Yellow
    }
} else {
    Write-Host "  OK: portfolio\holdings.json already present" -ForegroundColor Green
}
# The Yahoo Finance MCP server is not vendored here. Clone it separately and set its
# path in .mcp.json (see bootstrap\README.md, Setup). This step never hard-fails.
$mcpJson = Join-Path $FA_ROOT ".mcp.json"
if ((Test-Path $mcpJson) -and (Select-String -Path $mcpJson -SimpleMatch "/ABSOLUTE/PATH/TO/" -Quiet)) {
    Write-Host "  TODO: set the yahoo-finance path in .mcp.json (see README Setup)" -ForegroundColor Yellow
} else {
    Write-Host "  OK: yahoo-finance path in .mcp.json is configured" -ForegroundColor Green
}

# --- 5. Validation ---
Write-Host "[5/5] Running validation (check.py)..."
if ($pyCmd -and $allGood) {
    $checkScript = Join-Path $PSScriptRoot "check.py"
    & $pyCmd $checkScript
    if ($LASTEXITCODE -ne 0) { $allGood = $false }
} else {
    Write-Host "  SKIPPED (earlier steps failed)" -ForegroundColor Yellow
}

# --- Summary ---
Write-Host ""
if ($allGood) {
    Write-Host "=== READY ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Open Claude Code with FA/ as working directory:"
    Write-Host "  - VSCode: File > Open Folder > $FA_ROOT"
    Write-Host "  - CLI: cd `"$FA_ROOT`" && claude"
    Write-Host ""
    Write-Host "First test: type /market-pulse in Claude Code"
} else {
    Write-Host "=== INCOMPLETE ===" -ForegroundColor Red
    Write-Host "Fix the items marked above, then re-run: .\bootstrap\setup.ps1"
}
Write-Host ""
