# DSI 풀 생성 웹앱

회사 + RFP + 비즈니스 결정을 고르면 **제안서 `.hwpx` / `.pdf`** 를 생성하는 로컬 웹앱.
Claude Code 의 `/rfp` 흐름(rfp-analyst → proposal-writer → 양식 채움 → 빌드)을
**Anthropic API** 로 옮긴 것. 회사·RFP·양식은 전부 변수 — 특정 사업 키워드 하드코딩 없음.

## 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit UI — 회사▼ · RFP▼ · 결정 폼 · [생성] / [재빌드] |
| `pipeline.py` | 백엔드 — 두 LLM 호출 + 결정적 스크립트 오케스트레이션 |

- **정책 정본은 그대로 재사용**: 시스템 지침 = `.claude/agents/rfp-analyst.md` ·
  `proposal-writer.md` + 참조 skill(`korean-public-rfp` · `proposal-korean-style` ·
  `dabeeo-profile`). 정책을 복제하지 않고 *로드*만 한다.
- **인증 = Claude Max 구독** (`claude-agent-sdk`): 로그인된 Claude Code CLI 의 구독으로
  호출 → **API 크레딧 0**. (raw API SDK 가 아니라 Agent SDK 사용 — Anthropic 공식 "Max로 빌드".)
- **KB·양식은 프롬프트(user 메시지)에 주입**: Agent SDK 호출은 KB 전체 + form.yaml 을
  user 메시지에 넣는다. **Windows argv 한도** 때문에 정책·KB 같은 대형 내용은 `system_prompt`
  가 아니라 **stdin 스트리밍(async 제너레이터)** 으로 보낸다 (system_prompt 는 짧게 유지).

## 사전 준비

```powershell
# 1) 의존성 (이미 설치돼 있으면 생략)
pip install -r webapp/requirements.txt

# 2) Claude Code 로그인 (Max 구독) — API 키 불필요
#    이미 이 PC에서 Claude Code 에 로그인돼 있으면 그대로 동작.
claude   # 최초 1회 로그인 (브라우저 인증)
```

> **인증 안내**: 이 웹앱은 **Claude Max 구독**으로 호출한다(별도 API 키·크레딧 불필요).
> `ANTHROPIC_API_KEY` 가 환경에 있으면 (구독 대신)API 과금으로 새므로 webapp 이 자동 제거한다.
> 한 건 생성 환산 비용 ≈ **$2~4**(구독 차감, **별도 청구 없음**). 약 **15~25분**(본문 생성 + 한컴 PDF 변환).
> 빌드 단계(.hwp↔.hwpx, PDF)는 **한컴 오피스(Windows COM)** 가 설치된 PC 에서만 동작.

## 실행

```powershell
streamlit run webapp/app.py
```

브라우저가 열리면:

### ① 풀 생성 (~15~25분)
1. **과제 선택** — 상위 레벨 과제 하나만 고른다. 과제별 RFP·양식 매핑은 내부 정의
   (`webapp/projects.yaml`) — 사용자는 파일을 알 필요 없음.
2. **비즈니스 결정** 입력 — 신청형태(단독/컨소시엄) · 신청유형 · 사업비(국고억·비율) ·
   제품명 · 참여인력 표기(OOO/실명). *RFP·KB로 자동 안 되는 사람 결정만.*
3. **[제안서 생성]** → 진행 로그가 실시간 표시 → 완료 시 `.hwpx`/`.pdf` 다운로드.

> **과제 추가** = `webapp/projects.yaml` 에 한 항목(`name`·`rfp`·`form`) 추가하면 끝
> (rfp/form 은 `samples/rfp_downloaded/` 파일명; 둘 다 있어야 드롭다운에 노출). 코드 수정 0.

산출물은 `output/<날짜>/<회사>_<rfp>/` 에 저장 (`decisions.yaml` ·
`rfp_analysis.yaml` · `form.yaml` · `fills_total.yaml` · `*_채움.hwpx` · `별지_본체.pdf`).

### ② 재빌드 (LLM 없이, ~20초·무료)
이미 생성된 폴더를 골라 **빌드만** 다시. `fills_total.yaml` 을 손으로 고친 뒤
반영하거나, 검토용(녹색)↔제출본(검정)을 전환할 때 사용. API 호출 없음.

## 새 회사·새 RFP 추가

- **회사**: `kb/company/<새회사>/` 폴더 + `profile.yaml`(필수) · `finance.yaml`(선택) ·
  `*.md` 자료. 코드 수정 0 — 드롭다운에 자동 노출.
- **RFP/양식**: `samples/rfp_downloaded/` 에 공고·양식 파일을 넣으면 드롭다운에 자동 노출.

## 주의

- 채움 글자는 **검토용 녹색(#00AA00)** 이 기본(설계 의도 — 양식↔생성 구분). 발주처 제출 시에만
  *제출본(검정)* 체크.
- 생성된 내용은 **반드시 사람 검토** 후 제출. `(확인 필요)` 항목은 실값으로 교체 필요.
- 사업비·신청유형 등 전략 결정은 *가정 금지* — 미입력 시 해당 셀은 `(확인 필요)` 로 남는다.
