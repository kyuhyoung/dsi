# DSI — Dabeeo Super Intelligence

다비오 사내 AI 활용 공모전 산출물. RFP를 입력하면 제안서(`.docx`)와 발표자료(`.pptx`)를 자동 생성하는 시스템.

## 폴더 구조

```
dsi/
├── .claude/                  # Claude Code 환경 설정
│   ├── CLAUDE.md             # DSI 페르소나·전체 행동 규칙
│   ├── agents/               # 전문 에이전트 (자동 위임)
│   │   ├── rfp-analyst.md
│   │   ├── proposal-writer.md
│   │   └── ppt-designer.md
│   ├── commands/             # 슬래시 명령 (수동 호출)
│   │   └── rfp.md
│   └── skills/               # 도메인·문서 스킬
│       ├── korean-public-rfp/        # 한국 공공 RFP 분석 패턴
│       ├── dabeeo-profile/           # 다비오 회사 프로필
│       ├── proposal-korean-style/    # 한국어 제안서 스타일
│       ├── ppt-presentation-structure/  # 발표자료 표준 구성
│       ├── docx/             # 공식 .docx 생성·편집 (Anthropic)
│       └── pptx/             # 공식 .pptx 생성·편집 (Anthropic)
├── kb/                       # 회사 지식베이스 (파일 폴더 RAG)
│   ├── company/
│   ├── projects/
│   ├── proposals/
│   └── tech/
├── scripts/                  # 보조 스크립트 (현재 비어있음)
├── templates/                # Word/PPT 양식 파일 (회사 양식 도착 시)
├── docs/                     # 설계 문서·회의록
├── examples/                 # 샘플 RFP (테스트용)
├── install.sh                # 환경 설정 자동화
└── README.md
```

## 빠른 시작

```bash
# 1. 환경 설정 (Python 의존성 + 도구 확인)
./install.sh

# 2. Claude Code로 이 디렉토리에서 시작
claude

# 3. 슬래시 명령 실행
/rfp <RFP 파일 경로>
```

예시:
```
/rfp examples/sample-rfp.md
/rfp ~/Downloads/공항IT_2024.pdf
```

## 의존성

### 필수
- **Claude Code** (Team plan 이상)
- **Python 3.10+**
- `python-docx` (Word 생성)
- `python-pptx` (PowerPoint 생성)

### 선택 (고급 기능)
- `pandoc` — Word 텍스트 추출, 변환
- `libreoffice` — `.doc` → `.docx` 변환, PDF 변환
- `pdftoppm` (`poppler-utils`) — PDF → 이미지

Python 패키지 설치:
```bash
pip3 install --user python-docx python-pptx
```

선택 도구 설치 (Ubuntu/Debian):
```bash
sudo apt install pandoc libreoffice poppler-utils
```

## 작동 흐름

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

## 라이선스

- 본 프로젝트 (DSI): 다비오 사내 자산
- `.claude/skills/docx/`, `.claude/skills/pptx/`: Anthropic Proprietary (각 폴더의 `LICENSE.txt` 참조)
- `.claude/skills/korean-public-rfp/`, `dabeeo-profile/`, `proposal-korean-style/`, `ppt-presentation-structure/`: 다비오 사내 자산

## 문서

- [`docs/architecture.md`](docs/architecture.md) — 환경 설계 v1.0
- [`kb/INDEX.md`](kb/INDEX.md) — 지식베이스 색인·작성 규칙
