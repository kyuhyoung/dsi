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
│   └── skills/               # 자동 발동 스킬 (필요시 추가)
├── scripts/                  # Word/PPT 생성 파이썬 스크립트
├── templates/                # Word/PPT 양식 파일
├── docs/                     # 설계 문서·회의록
├── examples/                 # 샘플 RFP (테스트용)
└── README.md
```

## 사용법

```
/rfp <RFP 파일 경로>
```

TODO: 환경 설정·실행 가이드
