# DSI 사용 가이드

처음 이 repo를 받는 사람을 위한 빠른 시작·시연 안내.

## 두 가지 시작점

| 가지고 있는 것 | 사용 명령 | 단계 수 | 산출물 |
|---|---|---|---|
| **RFP 파일** (제안서 작성 안 됨) | `/rfp <파일>` | 7단계 | `.docx` 제안서 + `.pptx` 발표자료 + `.pdf` |
| **이미 작성된 제안서** | `/proposal <파일>` | 4단계 | `.pptx` 발표자료 + `.pdf` |

지원 포맷: `.md` `.txt` `.docx` `.hwp` `.hwpx` `.pdf`

## 5분 안에 첫 처리하기

### 사전 준비 (한 번만)

```bash
git clone ssh://git.dabeeo.net:3022/kevin.choi/dsi.git
cd dsi
./install.sh
```

`install.sh` 실행 결과 마지막에 *"=== 설정 완료 ==="* 가 보이면 준비 끝.

### 첫 실행 — RFP에서 시작

```bash
claude
# 그 후:
/rfp samples/rfp_downloaded/피지컬AI연구_제안요청서.hwp
```

### 첫 실행 — 제안서에서 시작

```bash
# 제안서 파일을 samples/proposals/ 에 떨궈놓고:
claude
/proposal samples/proposals/<제안서>.hwp
```

### 진행 흐름 (/rfp)

각 단계마다 결과 보여주고 *"진행"* 응답 대기:

```
[1/7] RFP 분석 중... (.hwp 자동 변환 포함)
       → analysis.yaml 보여줌. 누락·위험 항목 확인.
       → "진행" 입력

[2/7] 본문 작성 중... (KB 검색)
       → 제안서 본문 .md 보여줌. 톤·내용 검토.
       → "진행" 또는 "수정: <내용>"

[3/7] .docx 생성 중...
       → output/<날짜>/제안서_*.docx 경로 안내

[4/7] 슬라이드 구성 중... (간지·레이아웃·차트 자동 결정)
       → slides_*.yaml 보여줌. 분량·시각화 검토.
       → "진행"

[5/7] .pptx 생성 중... (회사 템플릿 자동 선택)
       → output/<날짜>/발표자료_*.pptx

[6/7] PDF 자동 변환 (LibreOffice headless)
       → output/<날짜>/발표자료_*.pdf

[7/7] 완료. 산출물 목록 + (선택) /preview 안내
```

### 진행 흐름 (/proposal — RFP 단계 스킵)

```
[1/4] 제안서 텍스트 추출 (HWP → 평문 + 이미지 자동 dump)
[2/4] 사업명·발주처 자동 추출 후 사용자 확인
[3/4] 슬라이드 구성 yaml 작성 (ppt-designer)
[4/4] 빌드 → .pptx → .pdf
```

### 빌드 후 검토

```
/preview output/<날짜>/발표자료_*.pptx
```

Claude가 슬라이드별 PNG 추출 후 시각 검토 → 이슈 보고.

## 회사 템플릿 추가

```bash
cp ~/Downloads/회사_template.pptx templates/
# Claude Code 안에서:
/onboard-template
# → 자동 발견 + 분석 + (필요 시) vision 보강 → style.yaml 작성
# 이후 /rfp 또는 /proposal 빌드 시 자동 사용
```

`/onboard-template` 동작:
- 인자 없음: `templates/*.pptx` 스캔, 새/변경된 template만 처리
- 인자 `<name>`: 특정 template 강제 재처리
- `--force`: 모든 template 재처리

template 종류별 처리:
- **디자인 가이드 ppt** (V1 같은 견본 컬렉션, placeholder + 안내문): 자동 분석만으로 충분
- **발표 자료** (실제 콘텐츠 + 디자인 융합): vision 보강 필요 — `/onboard-template`가 자동 호출
- **깔끔 정리본** (디자인만 살린 빈 견본): 자동 분석으로 빠르게 처리

자세한 자동 추론 항목은 [README.md](../README.md) 참조.

## 응답어 약속

| 입력 | 의미 |
|---|---|
| `진행` `다음` `ok` | 다음 단계로 |
| `수정: <내용>` | 현재 단계 결과 수정 요청 |
| `중단` `종료` | 현재까지만 저장 후 종료 |

## 실제 RFP 처리 시

```bash
# 사내 어디든 RFP 파일 둠
cp /shared/incoming/공항IT_2026.pdf examples/
# 또는 절대 경로로 처리
```

Claude Code 안에서:
```
/rfp /absolute/path/to/공항IT_2026.pdf
/rfp ~/Downloads/공항IT_2026.pdf
/rfp examples/공항IT_2026.pdf
```

PDF/Word 모두 native 지원.

## 시연 시나리오 (5/14 회의 또는 5/30 데모용)

### 30초 소개

> "이 시스템은 RFP 한 건을 받아 제안서(.docx)와 발표자료(.pptx)를 생성합니다.
> 단계별 사람 검토를 받아 품질을 보장하며, 한국어 격식체와 회사 정보를 자동 적용합니다."

### 1분 시연

```bash
$ claude
> /rfp examples/sample-rfp.md
[1/6] RFP 분석 중...
[1/6] 분석 완료. ✋ 검토 요청.
       → 화면에 누락 항목·위험 신호 강조 표시
> 진행
[2/6] 본문 작성 중...
[2/6] 본문 완료. ✋ 검토 요청.
> 진행
... (이하 동일)
[6/6] 완료. 산출물:
       - output/20260513/제안서_가상공항IT_v1.docx
       - output/20260513/발표자료_가상공항IT_v1.pptx
```

### 3분 심화

생성된 .docx 열어 확인:
- 평가배점에 비례한 섹션 분량 (추진방안 25점 → 본문 25%)
- TODO 표시로 KB 미확보 정보 명시 (추측 안 함)
- 격식체 일관 (*"당사는~합니다"*)

생성된 .pptx 열어 확인:
- 표준 슬라이드 순서 (표지→목차→회사소개→사업이해→...)
- 발표자 노트 자동 작성
- 평가배점 ↔ 발표 시간 매핑 검증 (YAML 마지막에 표 포함)

## 결과물이 마음에 안 들면

각 검토 지점에서 *수정* 응답:

```
> 수정: 사업 배경 부분을 발주처가 더 공감할 톤으로 바꿔줘
```

또는 작업 끝나고 .docx/.pptx 직접 편집해도 됨.
산출물 v1, v2, v3로 버전 자동 증가.

## 자주 묻는 질문

**Q. 회사 양식(.docx, .pptx) 적용은?**
A. `templates/` 폴더에 회사 양식을 두면 자동 적용. (양식 도착 대기 중)

**Q. 회사 자료(과거 제안서, 실적, 회사소개)는 어디에 두나요?**
A. `kb/` 폴더. 자세한 구조는 `kb/INDEX.md` 참조.

**Q. 한국어가 깨질 위험은?**
A. 사전 smoke test 통과 (`docs/smoke-test-20260513.md`). `.docx`/`.pptx` 모두 UTF-8 안전.

**Q. 외부에 데이터 보내나요?**
A. Claude API(Anthropic) 외에는 없음. KB 검색은 로컬 파일 시스템 내에서만.

**Q. 잘못 만들어진 결과로 입찰 들어가면?**
A. 생성된 산출물은 *초안*. 검토·수정·승인은 사람이 최종 책임.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `/rfp` 명령 인식 안 됨 | Claude Code가 `.claude/` 못 읽음 | `dsi/` 디렉토리 안에서 `claude` 실행 확인 |
| 한국어 깨짐 | python 패키지 누락 | `./install.sh` 다시 실행 |
| 산출물 안 만들어짐 | pandoc 등 선택 도구 없음 | `scripts/md2docx.py`, `yaml2pptx.py` 자동 fallback (이미 동작) |
| KB 검색 결과 비어있음 | `kb/` 채워지지 않음 | KB 자료 도착 대기, 또는 임시로 examples/ 활용 |

## 더 알고 싶으면

- `docs/architecture.md` — 시스템 설계
- `docs/smoke-test-20260513.md` — 검증 리포트
- `.claude/CLAUDE.md` — 페르소나·행동 규칙
- `.claude/agents/*.md` — 각 에이전트 상세
- `.claude/skills/*/SKILL.md` — 도메인 스킬 상세
