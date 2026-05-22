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

## 4. Claude memory — 환경별

`~/.claude/projects/-...-dsi/memory/` 의 *사용자 선호·feedback·project 메모*는 *환경별*. 회사에서 누적한 메모는 *집에 없음*.

해결책 (선택):
- (a) 메모리 동기화 안 함 — 각 환경 별도 학습 (자연스럽지만 일관성 떨어질 수 있음)
- (b) memory 폴더를 *수동 sync* (OneDrive·USB·git private repo 등)
- (c) 핵심 memory 파일만 *프로젝트 안에 복사* (예: `docs/memory-snapshot/`) — 새 환경에서 *Claude에 알려주기*

권장: (a) 또는 (c). 핵심 feedback (예: "근본 치유 선호"·"하드코딩 금지") 는 *대화 처음에 한 번 알려주면* 자동 학습됨.

## 5. 빠른 검증 (집에서 처음 켤 때)

```powershell
# 1. 의존성 동작 확인
python scripts/extract_hwp_form.py samples/rfp_downloaded/[양식]*.hwp /tmp/test.form.yaml
# → "표: 86개, 단락: 2242개" 출력 시 정상

# 2. 빌더 동작 확인
python scripts/form_to_docx.py `
    samples/rfp_downloaded/농식품AI_양식.form.yaml `
    output/D_10_농식품AI_filled_cells.yaml `
    output/D_test_v1.docx `
    --style templates/proposal_styles/농식품AI.style.yaml
# → "form_tables: 86, rendered: 86, filled_cells: 277" 출력 시 정상

# 3. .docx 열어보기
explorer.exe output\D_test_v1.docx
```

## 6. 문제 발생 시

- **한글 깨짐** — `chcp 65001` 실행 또는 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()`
- **import 오류** — `pip install pyhwp python-docx lxml pyyaml` 재실행
- **soffice 못 찾음** — `install.ps1` 다시 실행해 LibreOffice 경로 확인
- **hwp5proc 없음** — `pip install pyhwp` 후 *PowerShell 재시작* (PATH 갱신)
