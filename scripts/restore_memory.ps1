# 인수인계 메모리 복원 (Windows PowerShell)
# 다른 PC 에서 clone 후 1회 실행: .\scripts\restore_memory.ps1
#
# slug 자동 생성 — 프로젝트 절대 경로의 슬래시/콜론을 '-' 로 변환
#   D:\work\dabeeo\dsi → D--work-dabeeo-dsi

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$src = Join-Path $projectRoot "docs\handover-memory"
# 경로 → Claude Code slug (슬래시/콜론/역슬래시를 '-' 로)
$slug = ($projectRoot -replace '[\\:/]', '-')
$dest = Join-Path $env:USERPROFILE ".claude\projects\$slug\memory"

Write-Host "프로젝트 경로: $projectRoot"
Write-Host "slug: $slug"
Write-Host "복원 대상: $dest"
Write-Host ""

if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
}
Copy-Item -Path (Join-Path $src "*.md") -Destination $dest -Force
Write-Host ""
Write-Host "복원 완료: $dest"
Get-ChildItem $dest
