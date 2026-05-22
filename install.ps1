# DSI — Windows PowerShell 설치 스크립트
#
# 용법: PowerShell 에서 프로젝트 루트로 이동 후
#       .\install.ps1
#
# - 로그: 같은 폴더에 install.ps1.log (실행마다 덮어쓰기)
# - Python 의존성 + 외부 도구 존재 확인

$ErrorActionPreference = "Continue"
$logFile = Join-Path $PSScriptRoot "install.ps1.log"

# 로그 함수 — 콘솔 + 파일 동시 출력 (즉시 flush)
function Write-Log {
    param([string]$msg, [string]$color = "White")
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line -ForegroundColor $color
    $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

# 로그 초기화 (덮어쓰기)
"" | Out-File -FilePath $logFile -Encoding utf8
Write-Log "DSI 설치 시작 — Windows PowerShell" "Cyan"
Write-Log "프로젝트 루트: $PSScriptRoot"
Write-Log ""

# 한글 인코딩 (콘솔 UTF-8)
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# ───────────────────────────────────────────────
# 1. Python 확인
# ───────────────────────────────────────────────
Write-Log "[1/5] Python 확인" "Yellow"
$pythonCmd = $null
foreach ($cmd in @("python", "py", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            Write-Log "  ✓ $cmd : $version" "Green"
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Log "  ✗ Python 없음. https://python.org 에서 3.10+ 설치 후 PATH 추가." "Red"
    exit 1
}
Write-Log ""

# ───────────────────────────────────────────────
# 2. pip 의존성 설치
# ───────────────────────────────────────────────
Write-Log "[2/5] Python 패키지 설치" "Yellow"
$packages = @("pyhwp", "python-docx", "lxml", "pyyaml")
foreach ($pkg in $packages) {
    Write-Log "  pip install $pkg ..."
    $proc = Start-Process -FilePath $pythonCmd -ArgumentList "-m", "pip", "install", "--upgrade", $pkg `
        -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$logFile.pip.out" -RedirectStandardError "$logFile.pip.err"
    Get-Content "$logFile.pip.out" -ErrorAction SilentlyContinue | ForEach-Object { Write-Log "    $_" }
    Get-Content "$logFile.pip.err" -ErrorAction SilentlyContinue | ForEach-Object { Write-Log "    $_" "Red" }
    if ($proc.ExitCode -eq 0) {
        Write-Log "  ✓ $pkg 설치됨" "Green"
    } else {
        Write-Log "  ✗ $pkg 실패 (exit $($proc.ExitCode))" "Red"
    }
}
Remove-Item "$logFile.pip.out", "$logFile.pip.err" -ErrorAction SilentlyContinue
Write-Log ""

# ───────────────────────────────────────────────
# 3. 외부 도구 (LibreOffice·Chrome·hwp5proc) 확인
# ───────────────────────────────────────────────
Write-Log "[3/5] 외부 도구 확인" "Yellow"

# LibreOffice (docx → pdf 변환)
$sofficePaths = @(
    "C:\Program Files\LibreOffice\program\soffice.exe",
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe"
)
$soffice = $sofficePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($soffice) {
    Write-Log "  ✓ LibreOffice: $soffice" "Green"
} else {
    Write-Log "  ✗ LibreOffice 없음. https://www.libreoffice.org/ 설치 권장 (.docx → .pdf 변환용)" "Yellow"
}

# Chrome (hwp html → pdf)
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($chrome) {
    Write-Log "  ✓ Chrome: $chrome" "Green"
} else {
    Write-Log "  ! Chrome 없음 (시각 검증 용도, 필수 아님)" "Yellow"
}

# hwp5proc (pyhwp 설치 시 PATH 에 자동 등록)
try {
    $hwp5proc = & hwp5proc --help 2>&1 | Select-Object -First 1
    Write-Log "  ✓ hwp5proc 사용 가능" "Green"
} catch {
    Write-Log "  ✗ hwp5proc 실행 실패. pip install pyhwp 후 PATH 재시작 필요." "Red"
}
Write-Log ""

# ───────────────────────────────────────────────
# 4. 한컴오피스 풀버전 확인 (선택)
# ───────────────────────────────────────────────
Write-Log "[4/5] 한컴오피스 확인 (선택)" "Yellow"
$hncPaths = @(
    "C:\Program Files (x86)\Hnc",
    "C:\Program Files\Hnc"
)
$hncFound = $false
foreach ($p in $hncPaths) {
    if (Test-Path $p) {
        Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Log "  발견: $($_.FullName)"
            if ($_.Name -match "Office\s*\d+$") {
                Write-Log "  ✓ 한컴오피스 풀버전 추정 — pyhwpx 자동화 가능" "Green"
                $hncFound = $true
            } elseif ($_.Name -match "Viewer") {
                Write-Log "  ! 뷰어 (편집 불가) — .hwp 자동 편집 불가능" "Yellow"
            }
        }
    }
}
if (-not $hncFound) {
    Write-Log "  한컴 풀버전 미확인 — .hwp → .docx 변환 시 사용자 1회 작업 필요" "Yellow"
}
Write-Log ""

# ───────────────────────────────────────────────
# 5. 시각 검증 도구 (선택) — poppler·ImageMagick
# ───────────────────────────────────────────────
Write-Log "[5/5] 시각 검증 도구 (선택)" "Yellow"
try { pdftoppm -v 2>&1 | Out-Null; Write-Log "  ✓ pdftoppm (poppler)" "Green" }
catch { Write-Log "  ! pdftoppm 없음 (PDF → PNG 검증용, 필수 아님)" "Yellow" }
try { magick -version 2>&1 | Out-Null; Write-Log "  ✓ ImageMagick (magick)" "Green" }
catch {
    try { convert -version 2>&1 | Out-Null; Write-Log "  ✓ ImageMagick (convert)" "Green" }
    catch { Write-Log "  ! ImageMagick 없음 (선택)" "Yellow" }
}
Write-Log ""

# ───────────────────────────────────────────────
# 결과 요약
# ───────────────────────────────────────────────
Write-Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-Log "DSI 설치 완료. 로그: $logFile" "Cyan"
Write-Log ""
Write-Log "다음 단계:" "Cyan"
Write-Log "  1. claude code 실행 (Claude Code CLI 설치되어 있으면)"
Write-Log "  2. /rfp <RFP 파일> 또는 /proposal <제안서 파일> 으로 작업 시작"
Write-Log "  3. 산출물: output/ 폴더"
Write-Log ""
