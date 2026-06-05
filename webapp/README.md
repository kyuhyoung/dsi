# Dabeeo Super Intelligence — 풀 생성 웹앱

**RFP 과제**와 **신청 정보**를 고르면 **제안서 `.hwpx` / `.pdf`** 를 생성하는 로컬 웹앱.
Claude Code 의 `/rfp` 흐름(rfp-analyst → proposal-writer → 양식 채움 → 빌드)을
**Claude Max 구독**(`claude-agent-sdk`)으로 옮긴 것. 회사·RFP·양식은 전부 변수 — 특정 사업 키워드 하드코딩 없음.

## 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit UI — 과제▼ · 신청 정보 폼 · [생성] / [재빌드] |
| `pipeline.py` | 백엔드 — 두 LLM 호출(구독) + 결정적 스크립트 오케스트레이션 |
| `projects.yaml` | **과제 정의**(name·rfp·form). 사용자는 name 만 고름 |
| `run_once.py` | CLI 실측 러너(웹 없이 1건 생성·시간 측정) |
| `../제안서_웹앱_실행.bat` | **더블클릭 실행기**(프로젝트 루트) |

- **정책 정본은 그대로 재사용**: 시스템 지침 = `.claude/agents/rfp-analyst.md` ·
  `proposal-writer.md` + 참조 skill(`korean-public-rfp` · `proposal-korean-style` · `dabeeo-profile`).
  정책을 복제하지 않고 *로드*만 한다.
- **인증 = Claude Max 구독** (`claude-agent-sdk`): 로그인된 Claude Code CLI 의 구독으로
  호출 → **API 크레딧 0**. (raw API SDK 가 아니라 Agent SDK — Anthropic 공식 "Max로 빌드".)
- **KB·양식은 user 메시지에 주입 + stdin 스트리밍**: Agent SDK 호출은 KB 전체 + form.yaml 을
  user 메시지에 넣는다. **Windows argv 한도(WinError 206)** 때문에 정책·KB 같은 대형 내용은
  `system_prompt`(argv)가 아니라 **stdin 스트리밍**(`prompt=async 제너레이터`)으로 보낸다.
- **제안사 = 다비오 고정**(사내용 — UI 회사 선택 없음). 단 엔진은 `company` 변수라 회사 교체 가능.

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

**가장 쉬움 — 더블클릭**: 프로젝트 루트의 **`제안서_웹앱_실행.bat`** 더블클릭 → 잠시 뒤 브라우저가
`http://localhost:8501` 자동 오픈. (같이 뜨는 검은 창 = 웹 서버. 끄려면 그 창에서 `Ctrl+C` 또는 창 닫기.)

**또는 명령으로**:

```powershell
python -m streamlit run webapp\app.py
```

> `streamlit` 명령이 PATH 에 없을 수 있어 `python -m streamlit` 로 부른다.
> `pipeline.py` 를 수정하면 자동 반영이 안 되니 `Ctrl+C` 후 다시 실행(모듈 캐시). `app.py` 만 바꿀 땐 브라우저 새로고침.

### ① 풀 생성 (~15~25분)
1. **과제 선택** — 상위 레벨 과제 하나만 고른다. 과제별 RFP·양식 매핑은 내부 정의
   (`webapp/projects.yaml`) — 사용자는 파일을 알 필요 없음.
2. **신청 정보 (직접 입력 항목)** — RFP·KB에서 자동으로 못 정하는, 사람이 결정할 항목:
   신청형태(단독/컨소시엄) · 신청유형 · 사업비(국고억·비율) · 제품명 · 참여인력 표기(OOO/실명).
3. **[제안서 생성]** → 진행 로그가 실시간 표시 → 완료 시 `.hwpx`/`.pdf` 다운로드.

> **과제 추가** = `webapp/projects.yaml` 에 한 항목(`name`·`rfp`·`form`) 추가하면 끝
> (rfp/form 은 `samples/rfp_downloaded/` 파일명; 둘 다 있어야 드롭다운에 노출). 코드 수정 0.

산출물은 `output/<날짜>/<회사>_<과제>/` 에 저장 (`decisions.yaml` ·
`rfp_analysis.yaml` · `form.yaml` · `fills_total.yaml` · `*_채움.hwpx` · `별지_본체.pdf`).

### ② 재빌드 (LLM 없이, ~20초·무료)
이미 생성된 폴더를 골라 **빌드만** 다시. `fills_total.yaml` 을 손으로 고친 뒤
반영하거나, 검토용(녹색)↔제출본(검정)을 전환할 때 사용. LLM 호출 없음.

## 새 과제·새 회사 추가 (코드 수정 0)

- **과제**: `webapp/projects.yaml` 에 `name`·`rfp`·`form` 한 항목 추가 (파일은 `samples/rfp_downloaded/`).
  rfp·form 둘 다 있어야 드롭다운에 노출. *현재 등록: 농식품AI · 민군규격표준화.*
- **회사**: `kb/company/<새회사>/` 폴더 + `profile.yaml`(필수) · `finance.yaml`(선택) · `*.md` 자료.
  로고는 `kb/company/<회사>/images/logo.*`(우측 상단 헤더에 표시).

## 주의

- 채움 글자는 **검토용 녹색(#00AA00)** 이 기본(설계 의도 — 양식↔생성 구분). 발주처 제출 시에만
  *제출본(검정)* 체크.
- 생성된 내용은 **반드시 사람 검토** 후 제출. `(확인 필요)` 항목은 실값으로 교체 필요.
- 사업비·신청유형 등 전략 결정은 *가정 금지* — 미입력 시 해당 셀은 `(확인 필요)` 로 남는다.

## 검증 (2026-06-05)

농식품AI × 다비오 1건 **end-to-end 완주** — 22분, 환산 $2.37(구독 차감),
별지 제3호 사업계획서 PDF 27p(26p 내용 채움) 생성. 본체 별지 자동 식별 정확.
