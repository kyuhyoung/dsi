# DSI — Dabeeo Super Intelligence

다비오 사내 AI 활용 공모전 산출물. RFP를 입력하면 제안서(`.docx`)와 발표자료(`.pptx`)를 자동 생성하는 시스템.

## 폴더 구조

```
dsi/
├── .claude/                  # Claude Code 환경 설정
│   ├── CLAUDE.md
│   ├── agents/               # rfp-analyst, proposal-writer, ppt-designer
│   ├── commands/             # /rfp 슬래시 명령
│   └── skills/               # 도메인·문서 스킬
├── kb/                       # 회사 지식베이스 (파일 폴더 RAG)
│   ├── company/, projects/, proposals/, tech/
├── scripts/                  # 자동화 스크립트
│   ├── analyze_template.py        # .pptx → raw.yaml (원시 추출만, LLM 의미 분석)
│   ├── yaml_to_pptx.py            # 콘텐츠 yaml + style → .pptx 생성
│   └── md_to_docx.py              # 제안서 본문 → .docx
├── templates/                # 회사 PPT 템플릿
│   ├── <company>.pptx        # ← 사용자가 추가
│   ├── <company>.raw.yaml    # ← analyze_template.py 추출
│   └── <company>.style.yaml  # ← /onboard-template (LLM) 작성
├── output/                   # 생성물 (YYYYMMDD/)
├── samples/                  # RFP·이미지 자산
├── docs/, examples/
├── requirements.txt          # Python 의존성
├── package.json              # Node.js 의존성 (mermaid-cli)
└── README.md
```

## 빠른 시작

```bash
# 1. 환경 설정 (Python·Node·LibreOffice 점검 + 의존성 설치)
bash install.sh

# 2. Claude Code로 이 디렉토리에서 시작
claude
```

## 슬래시 명령

| 명령 | 용도 | 입력 |
|---|---|---|
| `/rfp <파일>` | RFP → 제안서 + 발표자료 (시각 자동 검증 포함) | RFP `.pdf`/`.docx`/`.hwp`/`.hwpx` |
| `/proposal <파일>` | 이미 작성된 제안서 → 발표자료만 (시각 자동 검증 포함) | 제안서 `.md`/`.docx`/`.hwp`/`.hwpx`/`.pdf` |
| `/onboard-template [이름]` | 새 template 자동 분석·등록 (LLM vision 기반) | (선택) 템플릿 이름 |
| `/preview <pptx>` | 빌드된 발표자료 슬라이드 시각 검토 (수동) | `.pptx` 경로 |
| `/verify-template <name>` | 템플릿 자동 매핑 검증 (썸네일 vision 확인) | 템플릿 이름 |

예시:
```
/rfp samples/rfp_downloaded/피지컬AI연구_제안요청서.hwp
/proposal samples/proposals/사업계획서_최종본.hwp
/preview output/20260518/발표자료_AI상용화_V1.pptx
```

## 회사 템플릿 사용

`templates/` 폴더에 회사 표준 `.pptx` 파일을 떨궈놓고 `/onboard-template` 한 줄로 등록.

```bash
# 1. 새 template 추가
cp ~/Downloads/회사_template.pptx templates/

# 2. Claude Code 안에서 한 줄로 등록 (자동 분석 + vision 보강)
/onboard-template

# 3. 이후 /rfp 또는 /proposal 빌드 시 자동 사용
/proposal samples/proposals/제안서.hwp
```

`/onboard-template` 동작:
- 인자 없음: `templates/*.pptx` 자동 스캔 → 새/변경된 template만 처리
- 인자 명시: `/onboard-template <name>` — 특정 template만 처리
- `template-analyzer` subagent (LLM vision) 호출 → `<name>.style.yaml` 자동 작성

직접 빌드도 가능:
```bash
python3 scripts/yaml_to_pptx.py <slides.yaml> <out.pptx> --template 회사_template
```

* `.pptx` 수정 시 `/onboard-template <name>` 재실행으로 재분석

### Template 분석 — 모두 LLM vision 기반

`analyze_template.py --raw`가 *원시 데이터*만 추출 (의미 분석 0). `template-analyzer` agent가 raw.yaml + 썸네일 보고 *모두 자동 식별*:

| 항목 | 분석 책임 |
|---|---|
| 슬라이드 종류 매핑 (표지/목차/간지/회사소개/본문/감사) | LLM vision (썸네일 동등 검토) |
| 본문 변종 (기본·이미지·표·이단·차트) | LLM (시각적 다양성 판단) |
| 챕터 구조 (`chapters: {1: 이름, ...}`) | LLM (layout name 의미 분석) |
| 챕터별 견본 매핑 (간지·회사소개·본문 모두) | LLM (디자인 다양성 활용) |
| 챕터 라벨 (`chapter_labels`) 위치·포맷 | LLM (layout 라벨 좌표 추출) |
| slot_finders (title·sub·body·chap_no 등) | LLM (raw.yaml 좌표 참조) |
| 견본의 *디자인 자산 / 콘텐츠 자산 / 잔재* 3분류 | LLM (vision으로 명시 분류) |
| 잔재 좌표 (`remove_shape_coords`) | LLM (점선·dot 등 좌표 명시) |
| 보존 좌표 (`preserve_shape_coords`) | LLM (로고·footer 등 좌표 명시) |
| 색상 (회사 CI) | theme.xml 추출 + LLM 매핑 |
| dummy_texts (콘텐츠 텍스트) | LLM 견본 텍스트 추출 |

*PY 점수·키워드·휴리스틱 없음.* 어떤 template (한국어·영문·디자인 가이드·실콘텐츠) 도 일반화.

### 콘텐츠 측 자동 추론 (ppt-designer 에이전트)

| 항목 | 자동 |
|---|---|
| 슬라이드 종류 결정 (표지·목차·간지·본문·감사 등) | ✓ 본문 구조 분석 |
| 간지 슬라이드 자동 삽입 (목차 섹션 수 만큼) | ✓ 스킬 가이드 |
| 슬라이드별 `레이아웃` 키 선택 (image-focus·split·visual-only 등) | ✓ 콘텐츠 패턴 |
| 본문 표(`|` 구분자) → bar_chart/timeline/matrix_2x2 변환 | ✓ 스킬 가이드 |
| 이미지 caption 자동 생성 | ✓ 스킬 가이드 |
| 이미지 ≥2장 → 슬라이드 분리 | ✓ 스킬 가이드 |

### 콘텐츠 우선 원칙

견본 placeholder 매핑이 실패해도 yaml 콘텐츠는 **항상 화면에 표시**됩니다:
- 견본 매칭 시 → 견본 디자인 그대로 사용
- 매칭 실패 시 → 새 textbox로 본문 영역에 fallback
- 견본 없는 종류 (목차·감사) → 코드로 직접 그림
- 빈 큰 도형 (이미지 자리) → 콘텐츠 없을 때 자동 제거

이로써 *임의의 회사 template*에 대해 디버깅 없이 동작.

### 미세 조정이 필요할 때

분석 결과(`templates/<name>.style.yaml`)는 *초안*이므로 회사 CI 의도와 다르면 수정:

| 항목 | 수정 위치 |
|---|---|
| 색깔이 회사 톤과 다름 | `colors:` 섹션 |
| 표지/본문 견본이 다른 슬라이드여야 | `template.layouts:` |
| 가이드 텍스트 남아있음 | `sample_clone.clear_non_placeholder_text: true` |
| 우상단 라벨 위치·색 | `top_right_label:` |

## 의존성

### 필수
- **Claude Code** (Team plan 이상)
- **Python 3.10+** + `requirements.txt`

### 선택 (고급 기능)
- **Node.js** — Mermaid 다이어그램 자동 변환 (`npm install`)
- **LibreOffice** — `.pptx` → PDF 변환 (Windows 또는 WSL에 설치)
- `pandoc` — Word 텍스트 추출
- `pdftoppm` (`poppler-utils`) — PDF → 이미지

선택 도구 설치 (Ubuntu/Debian):
```bash
sudo apt install pandoc libreoffice poppler-utils
```

## 작동 흐름

### 자동 파이프라인 (`/rfp` 슬래시 명령)

```
[사용자] /rfp <파일>
   ↓
[Claude Code 메인 세션]
   ↓ 단계별 위임
[rfp-analyst] → [proposal-writer] → [ppt-designer]
   ↓                  ↓                    ↓
RFP 분석          본문 마크다운        슬라이드 YAML
                      ↓                    ↓
                 [docx skill]         [pptx skill]
                      ↓                    ↓
                  .docx 파일           .pptx 파일

각 단계에 검토 지점이 있어 사용자 승인 후 다음 단계 진행.
```

### PPT 빌드 흐름 (yaml_to_pptx.py)

```
[template 등록 — 사전 1회]  /onboard-template <name>
   ↓
[analyze_template.py --raw]  원시 데이터 추출 (PY, 의미 분석 없음)
   ↓
templates/<name>.raw.yaml
   ↓
[template-analyzer agent]  LLM vision이 raw.yaml + 썸네일 보고 의미 분석
   ↓
templates/<name>.style.yaml (chapters, layouts, slot_finders, remove_shape_coords, ...)

[빌드 — 매번]  python3 scripts/yaml_to_pptx.py <slides.yaml> <out.pptx> --template <name>
   ↓
[yaml_to_pptx.py]
   - style.yaml 로드 (chapter_labels, body 변종, 색·폰트, 잔재 좌표)
   - 견본 슬라이드 복제 (디자인 배경)
   - 잔재 좌표 매칭 shape 자동 제거
   - 콘텐츠 매핑 (placeholder 매칭 + textbox fallback)
   - layout 챕터 라벨 *덮어쓰기* (콘텐츠 yaml의 장번호·장이름)
   - 시각요소 그리기 (flow_arrow / matrix_2x2 / callout_cards 등)
   - LibreOffice headless로 PDF 변환

[빌드 후 — 자동]  visual-validator agent
   ↓
PNG 추출 + 10개 카테고리 검증 (text_overlap, truncation, chapter_labels, ...)
   ↓
critical / high / medium 발견 → 사용자에게 보고 + 어느 yaml 수정할지 안내
```

### 시각요소 yaml 스키마

```yaml
시각요소:
  - type: flow_arrow             # 가로 화살표 흐름
    items: [A, B, C, D]
  - type: matrix_2x2             # 2x2 매트릭스
    x_axis: ...
    y_axis: ...
    quadrants:                   # 값: str 또는 {label, body}
      Q1: {label: 'KORINDO', body: '본계약 추진'}
      Q2: '단순 문자열'
  - type: bar_chart              # 막대 차트
    title: ...
    categories: [...]
    series: {name: [...]}
    highlight_categories: [...]  # 강조 (선택) — gold 색
    # 또는 highlight_indices: [0, 1]
  - type: timeline               # 가로 타임라인
    items: [{label, content}, ...]
  - type: callout_cards          # 강조 카드 N개
    items: [{title, body}, ...]  # str·dict 둘 다 허용
  - type: image                  # 이미지 삽입
    path: 'kb/.../img.png'
    caption: '...'
  - type: mermaid                # Mermaid 다이어그램 (Node.js 필요)
    code: |
      graph LR
        A --> B
```

스키마 정의: `templates/visual_element_schema.yaml` — *필수·선택 키 + 흔한 실수 안내*. 빌더가 yaml 로드 시 검증.

### 시스템 자산 yaml (templates/)

| 파일 | 역할 |
|---|---|
| `system_defaults.yaml` | 시스템-wide 임계·typography·shape safety·정책 |
| `layout_vocabulary.yaml` | 시각요소 (flow·matrix·timeline·callout·bar_chart) 파라미터 |
| `role_keywords.yaml` | (legacy) 역할 키워드 + 임계 (현재 미사용) |
| `visual_element_schema.yaml` | 시각요소 yaml 스키마 정의 + 흔한 실수 안내 |
| `visual_validation_checklist.yaml` | visual-validator agent의 10개 검증 카테고리 |
| `<name>.style.yaml` | template별 자동 분석 결과 (LLM이 채움) |

## 라이선스

- 본 프로젝트 (DSI): 다비오 사내 자산
- `.claude/skills/docx/`, `.claude/skills/pptx/`: Anthropic Proprietary (각 폴더의 `LICENSE.txt` 참조)
- `.claude/skills/korean-public-rfp/`, `dabeeo-profile/`, `proposal-korean-style/`, `ppt-presentation-structure/`: 다비오 사내 자산

## 문서

- [`docs/architecture.md`](docs/architecture.md) — 환경 설계 v1.0
- [`kb/INDEX.md`](kb/INDEX.md) — 지식베이스 색인·작성 규칙
