# 인수인계 메모리 복원 (Windows PowerShell)
# 다른 PC 에서 clone 후 1회 실행: .\scripts\restore_memory.ps1

$src = Join-Path $PSScriptRoot "..\docs\handover-memory"
$dest = Join-Path $env:USERPROFILE ".claude\projects\D--work-dabeeo-dsi\memory"

if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
}
Copy-Item -Path (Join-Path $src "*.md") -Destination $dest -Force
Write-Host ""
Write-Host "복원 완료: $dest"
Get-ChildItem $dest
