# 집/타 환경 setup 가이드

회사 PC ↔ 집 PC 작업 이전 시 필요한 단계.

## 1. 저장소 clone + 설치

### Windows PowerShell (native)

```powershell
git clone git@github.com:kyuhyoung/dsi.git
cd dsi
chcp 65001
.\install.ps1
claude
```

### Linux / WSL / macOS

```bash
git clone git@github.com:kyuhyoung/dsi.git
cd dsi
bash install.sh
claude
```

## 2. git에 *없는* 자료 — 외부 sync 필요

clone 만으로는 *불완전*. 다음 자료는 *보안·크기 이유로 git 제외* — 외부 sync (Google Drive·OneDrive·USB) 필요.

### A. 회사 비밀 자료 (사용자 명시 비밀)

| 파일 | 위치 | 영향 |
|---|---|---|
| `templates/[다비오] 회사소개자료.pptx` | 회사 KB 원본 | 다비오 KB 작업 시 — 단 `kb/company/dabeeo/*.md` 가 *추출본*이라 git에 있음 → 대부분 작업 가능 |

→ 회사소개자료.pptx *복사 필요 시* 외부 sync.

### B. 외부 출처 자료 (옵션)

| 파일 | 위치 | 영향 |
|---|---|---|
| `samples/proposals/[2차 취합]...hwp` | D 사람 작성본 | D vs D⁹/¹⁰ 시각 비교·`learned_patterns` 재생성 시 필요 |
| `samples/proposals/[2차취합]_사업계획서.txt` | D 텍스트 추출본 | 학습 자산 |

→ 외부 sync 또는 *집 PC에 없으면* 시각 비교 단계 스킵.

### C. 산출물 (재생성 가능)

다음은 *git에 없음 + 재생성 가능*:

| 파일 | 재생성 방법 |
|---|---|
| `output/D_*.docx/pdf/md` | `python scripts/form_to_docx.py` 또는 `yaml_to_docx.py` 재실행 |
| `output/D_사람작성_*.pdf` | 사람 작성본 hwp → chrome 변환 (B 자료 필요) |
| `output/양식_chrome변환.pdf` | `hwp5html` + `chrome --print-to-pdf` |

## 3. 환경 차이 — 인지할 점

| 항목 | 회사 (WSL) | 집 (Windows native) |
|---|---|---|
| **경로** | `/mnt/d/work/dabeeo/dsi/...` | `D:\work\dabeeo\dsi\...` |
| **shell** | bash | PowerShell |
| **줄 끝** | LF | `.gitattributes` 자동 처리 |
| **Python** | `python3` | `python` 또는 `py` |
| **LibreOffice** | `/mnt/c/Program Files/.../soffice.exe` | `C:\Program Files\LibreOffice\program\soffice.exe` |
| **Claude memory** | 회사 PC 에 누적 | 집 PC 에 별도 누적 (환경별) |

## 4. Claude memory — git 안에 백업 + 자동 복원

`~/.claude/projects/D--work-dabeeo-dsi/memory/` 의 *사용자 선호·feedback·project 메모*는 *환경별*. 회사에서 누적한 메모는 *집에 없음*. 해결책:

**`docs/handover-memory/` 안에 8개 핵심 메모리 백업** (git 안). clone 후 1회 복원:

### Windows PowerShell
```powershell
.\scripts\restore_memory.ps1
```

### Linux / WSL / macOS
```bash
bash scripts/restore_memory.sh
```

→ `~/.claude/projects/D--work-dabeeo-dsi/memory/` 에 자동 복사. Claude 다음 세션 부터 메모리 반영.

**핵심 메모리** (`docs/handover-memory/MEMORY.md` 인덱스):
- 양식 보존 원칙 — 양식 절대 안 만짐
- 일반화 원칙 — 임의 A·B·C 동작, 농식품AI 하드코딩 금지
- XML 결정적 채움 — 한컴 COM 변환 도구로만, 채움은 .hwpx XML 편집
- 본체 별지만 본격 산출 — 산출물 = 본체 별지 1개 .hwpx
- 본문 단락 생성·교체 = 핵심 가치 — "가나다" placeholder → 실제 본문
- 결과물 = 프로젝트 output 폴더
- 양식 모든 요소 = 의도 분류 + 일관성 보장

## 5. 빠른 검증 (집에서 처음 켤 때)

**필수**: 한컴오피스 2018 이상 설치 (.hwp ↔ .hwpx 변환 도구).

```powershell
# 0. pywin32 + pyhwp + lxml + pyyaml + pymupdf 설치
pip install pywin32 pyhwp lxml pyyaml pymupdf python-docx

# 1. .hwp → .hwpx 변환 (한컴 COM 동작 확인)
python scripts/hwp_to_hwpx.py "samples/rfp_downloaded/[양식] 농식품 분야 「AI 응용제품 신속상용화 지원사업」.hwp" /tmp/test.hwpx
# → "saved: ... (success=True)"

# 2. 양식 분석 (.hwpx → form.yaml + sections + fill_targets)
python scripts/extract_hwpx_form.py /tmp/test.hwpx /tmp/test.form.yaml
# → "표: 86, 빈 셀: 661, 별지: 7" 출력

# 3. fill (작은 fills 로)
echo "fills:
  - id: P56
    text: 테스트 본문" > /tmp/test_fills.yaml
python scripts/fill_hwpx_form.py /tmp/test.hwpx /tmp/test_fills.yaml /tmp/test_out.hwpx
# → "채움: 셀 0 + 단락 1 + ..."

# 4. 한컴으로 PDF 변환 (시각 확인)
python scripts/hwp_to_hwpx.py /tmp/test_out.hwpx /tmp/test_out.hwp  # 또는 SaveAs HWP
```

## 6. 현재 작업 이어가기

clone + restore_memory 후 Claude 에 한 마디만:

> "근본 치유 8차 이어서 진행. fills_본체별지3_v4 후 신청유형 체크박스 매핑 문제 남았음."

Claude 가 메모리 + git log + `output/20260524/E2E_v4_별지분리/` 확인 후 이어감.

**현재 진행 위치** (2026-05-26):
- v4 산출: `output/20260524/E2E_v4_별지분리/03_별지3_v4.pdf` (32 페이지)
- 채움 412 명세 / 셀 207 + 단락 54 + 셀안단락 13 + 체크 1
- 남은 갭: 신청유형 ☑ (label_or_content 분류 오류), 셀 매핑 오류 일부, 빈 셀 PDF render

## 7. 문제 발생 시

- **한글 깨짐 (콘솔)** — `chcp 65001` 또는 `$env:PYTHONIOENCODING="utf-8"`. yaml 파일 내용은 UTF-8 정상.
- **한컴 COM 안 됨** — `python -c "import win32com.client; hwp=win32com.client.Dispatch('HWPFrame.HwpObject'); print(hwp.Version); hwp.Quit()"` 으로 검증
- **import 오류** — `pip install pyhwp python-docx lxml pyyaml pymupdf pywin32` 재실행
- **hwp5proc 없음** — `pip install pyhwp` 후 *PowerShell 재시작* (PATH 갱신)
- **한컴 COM stuck (모달)** — `taskkill /F /IM Hwp.exe`. SaveAs 시간 길면 timeout 늘리기 (최대 5~10분)
- **메모리 안 보임** — `.\scripts\restore_memory.ps1` 재실행 후 Claude 재시작
