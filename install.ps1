# DSI Windows PowerShell installer
#
# Usage:
#   cd D:\work\dabeeo\dsi
#   .\install.ps1
#
# Log: install.ps1.log in the same folder (overwritten each run)

$ErrorActionPreference = "Continue"
$logFile = Join-Path $PSScriptRoot "install.ps1.log"

function Write-Log {
    param([string]$msg, [string]$color = "White")
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line -ForegroundColor $color
    $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

"" | Out-File -FilePath $logFile -Encoding utf8
Write-Log "DSI installer start (Windows PowerShell)" "Cyan"
Write-Log "Project root: $PSScriptRoot"
Write-Log ""

# UTF-8 console
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# ---------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------
Write-Log "[1/5] Python check" "Yellow"
$pythonCmd = $null
foreach ($cmd in @("python", "py", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            Write-Log "  OK $cmd : $version" "Green"
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Log "  FAIL Python not found. Install Python 3.10+ from https://python.org and add to PATH." "Red"
    exit 1
}
Write-Log ""

# ---------------------------------------------------------------
# 2. pip packages
# ---------------------------------------------------------------
Write-Log "[2/5] Python packages" "Yellow"
$packages = @("pyhwp", "six", "python-docx", "lxml", "pyyaml", "pywin32", "pymupdf")
foreach ($pkg in $packages) {
    Write-Log "  pip install $pkg ..."
    $proc = Start-Process -FilePath $pythonCmd -ArgumentList "-m", "pip", "install", "--upgrade", $pkg `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$logFile.pip.out" -RedirectStandardError "$logFile.pip.err"
    Get-Content "$logFile.pip.out" -ErrorAction SilentlyContinue | ForEach-Object { Write-Log "    $_" }
    Get-Content "$logFile.pip.err" -ErrorAction SilentlyContinue | ForEach-Object { Write-Log "    $_" "Red" }
    if ($proc.ExitCode -eq 0) {
        Write-Log "  OK $pkg installed" "Green"
    } else {
        Write-Log "  FAIL $pkg (exit $($proc.ExitCode))" "Red"
    }
}
Remove-Item "$logFile.pip.out", "$logFile.pip.err" -ErrorAction SilentlyContinue
Write-Log ""

# ---------------------------------------------------------------
# 3. External tools (LibreOffice, Chrome, hwp5proc)
# ---------------------------------------------------------------
Write-Log "[3/5] External tools" "Yellow"

$sofficePaths = @(
    "C:\Program Files\LibreOffice\program\soffice.exe",
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe"
)
$soffice = $sofficePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($soffice) {
    Write-Log "  OK LibreOffice: $soffice" "Green"
} else {
    Write-Log "  WARN LibreOffice not found. Install from https://www.libreoffice.org/ (docx to pdf)." "Yellow"
}

$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($chrome) {
    Write-Log "  OK Chrome: $chrome" "Green"
} else {
    Write-Log "  WARN Chrome not found (optional, used for hwp html to pdf)" "Yellow"
}

try {
    $hwp5proc = & hwp5proc --help 2>&1 | Select-Object -First 1
    Write-Log "  OK hwp5proc available" "Green"
} catch {
    Write-Log "  FAIL hwp5proc not on PATH. Restart PowerShell after pip install pyhwp." "Red"
}
Write-Log ""

# ---------------------------------------------------------------
# 4. Hancom Office (optional)
# ---------------------------------------------------------------
Write-Log "[4/5] Hancom Office (optional)" "Yellow"
$hncPaths = @(
    "C:\Program Files (x86)\Hnc",
    "C:\Program Files\Hnc"
)
$hncFound = $false
foreach ($p in $hncPaths) {
    if (Test-Path $p) {
        Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Log "  found: $($_.FullName)"
            if ($_.Name -match "Office\s*\d+$") {
                Write-Log "  OK Hancom full version detected (HwpObject COM ready)" "Green"
                $hncFound = $true
            } elseif ($_.Name -match "Viewer") {
                Write-Log "  WARN viewer only (edit not possible)" "Yellow"
            }
        }
    }
}
if (-not $hncFound) {
    Write-Log "  WARN Hancom full version not detected. hwp to hwpx auto conversion will fail." "Yellow"
}

# Verify HwpObject COM
try {
    $script = @"
import win32com.client
try:
    h = win32com.client.Dispatch('HWPFrame.HwpObject')
    print('COM_OK', h.Version)
    h.Quit()
except Exception as e:
    print('COM_FAIL', e)
"@
    $tmp = Join-Path $env:TEMP "dsi_check_hwp.py"
    $script | Out-File -FilePath $tmp -Encoding utf8
    $result = & $pythonCmd $tmp 2>&1
    Remove-Item $tmp -ErrorAction SilentlyContinue
    if ($result -match "COM_OK") {
        Write-Log "  OK HwpObject COM: $result" "Green"
    } else {
        Write-Log "  WARN HwpObject COM check failed: $result" "Yellow"
    }
} catch {
    Write-Log "  WARN HwpObject COM check skipped: $_" "Yellow"
}
Write-Log ""

# ---------------------------------------------------------------
# 5. Visual verification tools (optional)
# ---------------------------------------------------------------
Write-Log "[5/5] Visual verification tools (optional)" "Yellow"
try { pdftoppm -v 2>&1 | Out-Null; Write-Log "  OK pdftoppm (poppler)" "Green" }
catch { Write-Log "  WARN pdftoppm not found (optional)" "Yellow" }
try { magick -version 2>&1 | Out-Null; Write-Log "  OK ImageMagick (magick)" "Green" }
catch {
    try { convert -version 2>&1 | Out-Null; Write-Log "  OK ImageMagick (convert)" "Green" }
    catch { Write-Log "  WARN ImageMagick not found (optional)" "Yellow" }
}
Write-Log ""

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
Write-Log "===============================================" "Cyan"
Write-Log "DSI installer done. Log: $logFile" "Cyan"
Write-Log ""
Write-Log "Next steps:" "Cyan"
Write-Log "  1. .\scripts\restore_memory.ps1   (restore Claude memory)"
Write-Log "  2. claude                          (start Claude Code)"
Write-Log ""
