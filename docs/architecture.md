# DSI 환경 설계 (v1.0)

작성일: 2026-05-13
회의 일정: 2026-05-14 Claude 환경 설계

## 1. 한 줄 요약

다비오의 RFP 자동 제안서·발표자료 생성 시스템 — **Claude Code 기반**.

## 2. 도구 선택 (5/13 회의 결정사항)

| 후보 | 결과 | 이유 |
|---|---|---|
| Claude.ai Projects | ❌ | 자동화 한계 |
| **Claude Code** | ✅ | MCP·CLI 자동화, repo 정본, 팀 협업 |
| Claude Cowork | 보조 | 비개발자용 보조 경로로 추후 검토 |

## 3. 아키텍처

```
[사용자] /rfp <파일>
   ↓
[Claude Code 메인 세션 — DSI 페르소나]
   ↓ 단계별 위임
[rfp-analyst] → [proposal-writer] → [ppt-designer]
   ↓                  ↓                    ↓
RFP 분석          본문 마크다운        슬라이드 YAML
                      ↓                    ↓
                 [docx skill]         [pptx skill]
                      ↓                    ↓
                  .docx 파일           .pptx 파일

참조 자원:
- skills/ : 도메인 패턴 (RFP 분석·한국 제안서 스타일·회사 프로필·PPT 표준)
- kb/     : 회사 지식베이스 (파일 폴더 RAG)
```

## 4. 디렉토리 구조 (이미 repo에 반영됨)

```
dsi/
├── .claude/
│   ├── CLAUDE.md             # DSI 페르소나·워크플로우
│   ├── agents/               # 3개 전문 에이전트
│   ├── commands/rfp.md       # /rfp 슬래시 명령
│   └── skills/               # 4개 도메인 스킬
├── kb/                       # 지식베이스 (파일 폴더 RAG)
│   ├── company/
│   ├── projects/
│   ├── proposals/
│   └── tech/
├── templates/                # 회사 .docx/.pptx 양식
├── docs/                     # 설계·회의록
├── examples/                 # 샘플 RFP
└── README.md
```

## 5. 영역별 책임 (제안 — 회의에서 확정)

| 영역 | 산출물 | 담당 (예시) |
|---|---|---|
| Claude 환경 골격 | `.claude/*`, install, 기본 페르소나 | Claude 환경 리드 |
| 핵심 prompt | `CLAUDE.md`, `proposal-writer.md` | Claude 환경 리드 |
| PPT 디자인 prompt | `ppt-designer.md` | 디자인 담당 |
| KB 수집·세팅 | `kb/` 폴더 내용 | KB 담당 |
| KB 인터페이스 | 검색 절차 (Glob/Grep/Read) | Claude 환경 리드 (확정) |
| 회사 양식 | `templates/proposal.docx`, `deck.pptx` | 양식 담당 |
| 외부 도구 보안 협의 | 회사 보안팀 협상 | 보안 협의 담당 |

## 6. KB 인터페이스 (담당자 간 약속)

본 시스템은 Dify, AnythingLLM, NotebookLM Enterprise 등 어떤 KB 백엔드와도 호환 가능. 핵심은 `kb/` 폴더 검색 절차:

```
1. Glob "kb/**/*.md"      # 구조 파악
2. Grep "<키워드>" kb/    # 검색
3. Read <매치 파일>        # 읽기
```

**KB 담당이 어떤 도구로 가든, 결과 문서를 `kb/` 폴더에 정해진 구조(`kb/INDEX.md` 참조)로 두면 자동 동작.** 백엔드 변경 시 Claude 환경 측 코드 변경 0.

## 7. 5/30 데모 시나리오 (제안)

- 입력: 샘플 RFP 1건 (PDF)
- 명령: `/rfp examples/sample-rfp.pdf`
- 단계별 검토 지점 3개에서 *진행* 응답
- 출력: `.docx` 제안서, `.pptx` 발표자료
- 소요 시간: 5~10분
- 메시지: **"오늘부터 즉시 쓸 수 있고 (5/30 데모), 6/1 이후 KB·MCP 확장으로 전사 도입 가능"**

## 8. 일정 (담당 영역 기준)

| 기간 | 작업 | 담당 |
|---|---|---|
| 5/13 (선반영) | 환경 골격 생성 ✅ | Claude 환경 리드 |
| 5/13 (선반영) | 공식 docx/pptx skill 통합 + 한국어 검증 ✅ | Claude 환경 리드 |
| 5/14 | 환경 설계 회의 (본 문서로 합의) | 전원 |
| 5/15~20 | KB 수집·세팅 | KB 담당 |
| 5/15~20 | 회사 양식 `.docx`/`.pptx` 수집·정리 | 양식 담당 |
| 5/17~22 | 통합 테스트 (샘플 RFP로 end-to-end) | Claude 환경 리드 + KB 담당 |
| 5/22~25 | 발표 자료 제작 | 전원 |
| 5/26~29 | 리허설·버그 수정 | 전원 |
| 5/30~6/1 | PT, 시연 | 전원 |

## 9. 미결 안건 (회의에서 결정)

- [ ] EP 트랙(`ep/`)을 같은 repo에 둘지 분리할지
- [ ] 5/30 데모에서 *실제 KB 연동*을 보여줄지, mock으로 갈지
- [ ] 회사 보안팀에 외부 도구 사용 협의 누가·언제 시작할지
- [ ] 다비오 Google Workspace 라이선스 등급 확인 (Gemini Enterprise 여부)
- [ ] KB 백엔드 선택 (파일 폴더 / AnythingLLM / Dify / NotebookLM Enterprise)
- [ ] `dabeeo-profile/SKILL.md` TODO 채울 1차 자료 누가 제공할지

## 10. 후속

회의에서 결정·수정 사항 그 자리에서 본 문서에 반영. 회의 후 1시간 안에 v1.1로 커밋·푸시.
