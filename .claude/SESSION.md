# 세션 인수인계 — DSI

> **이 파일은 git에 들어가는 *다음 세션 Claude를 위한 인수인계*다.**
> 매 큰 라운드 종료 시 / commit 직전 갱신. CLAUDE.md 룰에 따라 모든 세션 시작 시 *가장 먼저* 읽힘.
> 메모리(~/.claude/projects/.../memory/)는 PC별이라 동기화 마찰 있음 — 핵심 인계 정보는 *여기*에 둠.

---

## 마지막 라운드 (2026-06-08, 집 PC) — webapp 완성도: 확인필요 축소 + UX + 캐시 + 날짜경계

**한 줄 결과**: webapp 품질·UX·속도 마감. **확인필요 38→21**(비율키버그+proposal강화), **폼 검증 가드**, **진행률 UI**, **PDF 캐시 연쇄(재실행 22분→0초)**, **outdir 날짜 무관화**.

**⚠️ 중요 변경 — webapp 산출물 경로**: `output/<날짜>/...` → **`output/_gen/<회사>_<과제>/`** (날짜 제거). 날짜 경계(자정) 넘어도 같은 폴더라 resume·캐시 작동. 다른 PC 재현/검토 시 *이 경로* 봄. (옛 날짜 폴더 20260604/20260607 는 잔존 — 정리 선택사항.)

**커밋 (이번 라운드, 전부 push):**
- `596b72d` requirements.txt ASCII화 (pip -r cp949 에러 해소).
- `837e599` **fill_budget 비율 robust** — rfp-analyst `국고_비율` vs fill_budget `국고비율` 키 불일치 버그 → 정규화+어휘 매칭(nested 평탄화) + `_first_pct` 순수숫자 인정. cross-form: 농식품 70/30/10/90, F16PBU 0. 사업비 비율 4건 확인필요 해소.
- `7494518` **proposal-writer 강화**(pipeline user: KB 수치목표 적극 + PII 헤더 OOO) → 수출목표 10억 채움·PII OOO. 확인필요 21로. 남은 21=정당 미확정(견적전·KB외, 추측 회피).
- `e608dc1` **폼 검증 가드**(app.py): 비율 합≠100 차단, 제품명·국고0 경고.
- `61d644a` **진행률 UI**(app.py): log 키워드→단계 progress bar + 경과시간(정상·resume 문구 모두).
- `a101ef5` **PDF 캐시**(hwpx_to_pdf: 출력≥hwpx면 변환 생략, --force) + 빌드/분할 캐시(pipeline).
- `16d9705` **outdir 날짜무관**(_gen/) + decisions 변경감지(결정 의존물 무효화) + merge 캐시 → 캐시 연쇄 완성. 재실행 0초 실증.

**재현 (다른 PC, git pull 후)**: webapp 셋업(`pip install claude-agent-sdk streamlit pyyaml PyMuPDF`, claude Max 로그인) → `제안서_웹앱_실행.bat` 또는 `python -m streamlit run webapp/app.py`. CLI 실측: `python webapp/run_once.py` (농식품×다비오, 산출 `output/_gen/dabeeo_농식품.../별지_본체.pdf` 27p). **이미 _gen/ 산출물 있으면 재실행 0초**(캐시).

**남은 미완/다음 후보**: ① 과제 추가(양식 확보 시 projects.yaml) ② 한컴 PDF 첫 변환 자체 속도(캐시 miss 시 분 단위 — 본질) ③ proposal 더 강화 or KB 보강. **B 비목 배치 엔진**(다른 R&D 양식 확보 후) 여전히 대기.

---

## (이전) 라운드 (2026-06-07, 집 PC) — webapp 셋업 + end-to-end 실측 → 버그 2건 근본수정

**한 줄 결과**: 집 PC webapp 첫 셋업 + 농식품×다비오 end-to-end 실측. 실측이 *버그 2건*을 잡아 근본 수정. **산출물 `output/20260607/.../별지3호.pdf` (27p)** — 이번까지 모든 수정(요약표 채움·비목더미0·단독신청 일괄·오배치0) webapp 자동생성에도 정상 반영 확인.

**셋업 (집 PC)**: `pip install claude-agent-sdk streamlit pyyaml PyMuPDF` (requirements.txt 직접 `-r` 은 한글주석 cp949 에러 → **ASCII화 커밋 `596b72d`** 로 해결). claude CLI Max 구독 로그인됨. streamlit 기동 OK(localhost:8501).

**버그①: rfp-analyst YAML 파싱 실패** (커밋 `4a53f9d`, `webapp/pipeline.py`):
- 원인: LLM 이 콜론·괄호 든 값을 quote 안 함 (`사업기간: 2026∼2027년 (타입1: 협약일)` → 값 안 콜론을 nested mapping 오인) → `yaml.safe_load` 실패 → 파이프라인 중단(PDF 0).
- 수정: `_call_llm_yaml()` 자가복구(파싱 실패 시 오류 피드백해 LLM 재생성, 최대 2회) + user 프롬프트 "콜론·특수문자 값 작은따옴표" 예방 지시. rfp-analyst·proposal-writer 공통. 재실측 시 첫 시도 통과(자가복구 0회).

**버그②: PDF 변환 20분 타임아웃 = 한컴 좀비** (이번 커밋, `scripts/hwpx_to_pdf.py`):
- 원인: 13일·7일 전 시작된 한컴 좀비 프로세스가 새 COM 변환을 hang → 첫 시도가 1200s 타임아웃까지 가서 재시도(무차별 taskkill)에 도달조차 못함. **좀비 정리 후 동일 변환 30초 완료**.
- 수정: `convert()` 시작 시 `_clear_stale_hwp(3600)` — StartTime 1시간+ 인 Hwp 좀비만 선제 정리(활성 GUI 편집은 임계로 보호). 모든 PDF 변환 공통.

**검증**: 별지3호.pdf 27p · 추진전략/목표시장/실현가능성 ❍채움 · 비목더미 0 · 협업="해당 없음(단독신청)" · 라벨 오배치 0 · OOO 35 · 확인필요 37(webapp 자동생성 보수적, 제출 전 교체).

**추가 — 확인필요 축소 (38→21)**: ① **사업비 비율 4건 = rfp-analyst↔fill_budget 키 불일치 버그**(rfp-analyst `국고_비율` vs fill_budget `국고비율`) → `ratios_from_rfp` robust 키 매칭(정규화+어휘, nested 평탄화) + `_first_pct` 순수숫자 인정. cross-form: 농식품 webapp·수동 70/30/10/90, F16PBU 0. 커밋 `837e599`. ② **proposal-writer 강화**(pipeline user: KB 수치목표 적극 + PII 헤더 OOO) → 수출목표 10억 채움·PII OOO 12. 커밋 `7494518`. **남은 21 = 정당 미확정**(견적전 단가·미확정 목표·KB외 인력 — 추측 회피가 정직, 수동본 10은 일부 생성/가정 포함).

**미완/다음 후보**: ① 한컴 PDF 변환 자체 속도(좀비 없어도 분 단위) ② 과제 추가 ③ 진행률 UI ④ 비즈니스 결정 폼 필수값 검증. **B 비목 배치 엔진**(다른 R&D 양식 확보 후) 여전히 대기.

---

## (이전) 라운드 (2026-06-05) — 풀 생성 웹앱 (webapp/) + Max 구독 인증 + 농식품 end-to-end 실증

**한 줄 결과**: RFP 과제 드롭다운 → 제안서 .hwpx/.pdf 생성하는 **Streamlit 웹앱(`webapp/`)** 구축. `/rfp` 흐름을 **Claude Max 구독(claude-agent-sdk)** 으로 옮김 — **API 크레딧 0**. 농식품×다비오 1건 **end-to-end 완주 실증**(22분, 별지3호 PDF 27p).

**구성**: `webapp/app.py`(UI) + `pipeline.py`(백엔드, 두 LLM 호출 + 기존 scripts 오케스트레이션) + `projects.yaml`(과제 정의) + `run_once.py`(실측 러너) + `README.md`. 제안사=다비오 **고정**(UI 회사칸 제거), 엔진은 `company` 변수 유지(일반성).

**핵심 결정·함정 (메모리 [[webapp-full-generation]] 에 상세)**:
- **인증 = Max 구독**, API 키 아님. **Claude Desktop $78.51 ≠ API Console 잔액**(별개 지갑 — API 키로 그 돈 못 씀; API 잔액은 소진됨). raw `anthropic` SDK → **`claude-agent-sdk`** 전환(Claude Code CLI 구독 로그인 사용). `ANTHROPIC_API_KEY` 가 env 에 있으면 (소진된)API 과금으로 새므로 **pop 필수**(app.py·run_once.py 둘 다 처리).
- **Windows argv 한도(WinError 206)**: Agent SDK 가 `system_prompt`·string `prompt` 를 argv 로 전달 → 정책+KB(109K자) 시 실패. 해결: 정책·KB·form 을 **user 메시지에 접어 stdin 스트리밍**(`prompt=async제너레이터`, 메시지 dict `{"type":"user","message":{"role":"user","content":...},"parent_tool_use_id":None}`), system_prompt 는 짧게.
- **resume**: 중간산출(rfp.txt·form.yaml·rfp_analysis·fills_profile/finance/budget) 있으면 재사용 — 실패 지점부터 이어받기(같은 outdir).
- **proposal-writer 범위 = 본체 별지 표범위로 한정**(rfp_analysis `table_idxs_range`, 농식품 [13,73]=609셀) — 출력 토큰 절감 + CLAUDE.md 포커스 정합.
- **과제 추가 = `webapp/projects.yaml` 한 항목**(name·rfp·form). 코드 수정 0. 현재 등록: 농식품AI·민군규격표준화(둘 다 rfp+양식 pair). F16PBU·피지컬AI·방산은 양식 불명확으로 제외.
- 로고: `kb/company/<회사>/images/logo.*`(규칙 파일명) → 우측 상단 헤더 이미지(배경 워터마크는 사용자가 "으스스"하다고 반려).

**실행**: 루트 **`제안서_웹앱_실행.bat` 더블클릭**(권장) 또는 `python -m streamlit run webapp/app.py`(streamlit 명령 PATH 없음 → `python -m`). pipeline.py 수정 후엔 Ctrl+C 후 재실행(모듈 캐시). 한컴 COM(Windows) 필요. UI: DSI(남색 그라데이션) 타이틀 · 과제 선택 · 신청 정보(직접 입력 항목) · 우측 상단 로고. README(루트·webapp 둘 다)에 스크린샷.

**🏠 다른 PC(집)에서 이어가기**:
1. `git pull github main` (아래 푸시 리모트 주의)
2. `pip install -r webapp/requirements.txt` — **`claude-agent-sdk` 신규 의존성**(+ streamlit·pyyaml·PyMuPDF). 집 PC엔 아직 없을 것.
3. `claude` 로그인(Max 구독) 확인 — Agent SDK가 이 로그인을 씀(API 키 불필요).
4. `제안서_웹앱_실행.bat` 더블클릭 → localhost:8501.
- **⚠️ 푸시/풀 리모트 = `github`(kyuhyoung/dsi)**, `origin`(사내 dabeeo git.dabeeo.net:3022) 아님. `git push github main` / `git pull github main`. origin은 SSH 키 인증이 환경따라 막힘.

**미완/다음 후보**: ① 한컴 PDF 변환 ~14분(제일 느림) 단축 ② 과제 더 추가(양식 확보 시) ③ 진행률 UI 개선 ④ 비즈니스 결정 폼 검증(필수값 미입력 가드). **B 비목 배치 엔진**(다른 R&D 양식 확보 후)은 여전히 대기.

---

## (이전) 라운드 (2026-06-04 심야2) — overfit 전수 감사 + #1~7 일반화 (매칭펀드 + 회사 정체성)

**한 줄 결과**: 전체 md/py/yaml overfit 4영역 병렬 감사 → 의심 목록. **#1~7 전부 일반화** — ① 정부 R&D 매칭펀드 전제(#1~4: 비R&D RFP서 동작) ② 다비오 정체성/예시(#5~7: 임의 회사 교체=KB 폴더 교체, md 수정0). 농식품 회귀 0.

**overfit 감사 — #1~7 전부 처리:**
- 🔴 **#1~4 정부 R&D 매칭펀드 전제 ✅완료**: #1 비율 70:30 fallback 제거(RFP/CLI 명시만, 미지정 확인필요) · #2 rfp-analyst 예산스키마 "[매칭펀드형만]"(비매칭펀드는 RFP 구조 그대로) · #3 fill_finance "백만원"/1000000 PY리터럴→무변환(한국 default=yaml proposal_output_unit) · #4 budget_vocab item_roles "R&D 전용·비R&D는 vocab 확장" 명시. 검증: 농식품 단위·비목인식·28.571 동일, F16PBU 0.
- 🟡 **#5~7 다비오 정체성/예시 ✅완료**: #5 CLAUDE.md 정체성·검증→"제안사(KB 회사)"(다비오=현재 인스턴스, 운영포커스 별지3호 유지) · #6 dabeeo-profile skill 본문 LIG 데모 메타→*회사무관 KB 라우팅*(회사정보=kb/company/{회사}/, skill 수정0) · #7 md 예시 "제안사:다비오"→플레이스홀더(3곳).
- 🟢 **저순위 잔여**(미수정): R&D용어(연구방안·End-to-End)·다국어 미지원(한국 더미정규식)·슬라이드수 매직. **✅ 깨끗**: korean-public-rfp, 빌더 PY 전반(yaml로드), label_map/schema.
- ✅ **회사별 KB 분리 완료**: LIG 데모(공용 `kb/projects/`·`kb/tech/`)를 `kb/company/lig/` 아래로 이동(`lig/projects/`·`lig/tech/`). **공용 실적/기술 폴더 폐지 — 회사 자료는 전부 `kb/company/{회사}/`**(다비오는 `dabeeo/projects.md`·`tech-core.md`로 이미 통합). 라우팅 갱신(CLAUDE.md·proposal-writer·rfp·dabeeo-profile·INDEX). 제안사 검색=해당 회사 폴더 범위→혼입 위험 제거. 임의 회사 추가=`kb/company/{새회사}/` 신설.

**#1 수정 (fill_budget_cells.py + budget_vocab.yaml)**: `ratio_defaults: {}`(fallback 제거). `ratios_from_rfp(rfp,vocab,cli)`는 RFP+CLI만, 미지정 None(한쪽만 있으면 100-보완). `compute_totals` None 가드. 비율 미지정 총괄셀 `(확인 필요)`. CLI `--gov-pct/--self-pct/--cash-pct/--in-kind-pct` 추가. 검증: ①농식품 미지정→확인필요(가정제거) ②농식품 CLI명시→28.571(회귀0) ③F16PBU→0 fills. **농식품 70:30은 이제 CLI 명시로** (조용한 가정 아님). fills_total 값 동일(영향0).

**🔧 재현 명령 변경 — fill_budget_cells 에 비율 CLI 필수**:
`python scripts/fill_budget_cells.py <form> <rfp_analysis> <out> --gov-eok 20 --type 타입1 --self-pct 30 --cash-pct 10 --in-kind-pct 90`
(비율 생략 시 총괄표 `(확인 필요)` — 정상. 농식품 비즈니스결정 70:30/현금10:현물90 명시.)

---

## (이전) 라운드 (2026-06-04 심야) — 이미지/전역일관성 md정책 + 정책 실증 재생성 + F16PBU cross-form

**한 줄 결과**: 사용자 지적(단독신청인데 4-4 컨소 섹션에 "컨소시엄 대체/IP공유 60:40" 모순, 이미지 2칸 처리)을 *개별 손수정 대신 md 정책으로 일반화* → proposal-writer 재호출로 **손수정 0 일관 재생성 실증**. 별도로 F16PBU(군수) 양식 전체 흐름 **코드수정0 완주**. 최종 `output/20260604/별지3호.pdf`.

**md 정책 (proposal-writer.md, 전부 일반 — 키워드·셀ID·절번호·임계 하드코딩 0):**
- **§5-2 이미지**: 칸 여러 개면 상보/중복을 *맥락*으로 판단 — 상보=각 칸 다른 측면(적합 이미지 없으면 "삽입 필요" 명세+제목), 중복/무차별=한 칸+나머지 빈칸. 캡션 제목=이미지 content_text 기반. **꺾쇠 `<>`·"제목" *표기*로 판별 금지**(농식품=캡션·F16PBU=사업명·민군=작성요령으로 의미 제각각 — 검증 박제).
- **§전역 결정 일관성**: 단독신청 등 전역 비즈니스 결정이 *셀 값뿐 아니라 전 섹션 서술·표현*에 일관. 컨소 전용 섹션 "해당없음"+단독사유 간결, "외부협력 대체/공동/IP공유" 모순 표현 금지, 일반 협력(산학·공급)은 역량 섹션 단독양립 표현. 자기검증(②)에 "전역결정 모순 서술·표현 0, 전 섹션" 추가.

**정책 실증 (이번 라운드 핵심 가치)**: proposal-writer 재호출 — fills_total을 강화정책 기준 재작성, 수치·PII·결정 *동결*. **전수점검 후 정책위반 단 2건**(T45 ※박스+IP공유 제거, P101 "컨소시엄 트랙"→"협력 트랙"), 나머지 바이트 동일. *내 손수정이 놓친 T45까지 정책이 잡음* = md 일반성 방증. 검증: 컨소대체·IP공유·공동수급·컨소트랙 0 · 단독신청 8 · OOO 21 · 28.571 · 확인필요 10 · 서술체 0.

**F16PBU cross-form (코드 수정 0)**: 군수 규격입찰 양식 전체 흐름(extract→매처→rfp분석→proposal→빌드→PDF 41p) 완주. extract 별지 자동검출, 회사매처 **0 오염**(회사정보칸 없는 양식), rfp-analyst 도메인미스 정직인식(다비오 부적합 판정), proposal-writer 억지매핑 0(영상DB 4셀만 KB근거, 나머지 역량외/확인필요/명세). **"안 맞는 양식엔 억지로 안 채우고 정직 처리"=일정 품질의 정의.** 산출물 `output/20260604/F16PBU/`.

**미완**: T66 terminator example_row *양성* 검증(같은 구조 다른 양식 부재 — 영향0만 증명). 빌더 "빈 fill 무시"(명시적 셀 clear 미지원 — 중복/무차별 칸 빈칸화는 명세로 우회). 별지밖 fill_company 재실행 정리 미적용(focus 별지3호).

---

## (이전) 라운드 (2026-06-04 밤) — T66 인건비표 누더기 근본수정 + example_row 마킹 일반화

**한 줄 결과**: 별지3호 전수 시각검토 중 발견한 T66 인건비 *명세*표 "절반만 비워진 누더기"(성명·월급여는 비고 직위·참여기간·참여율·합계 `대표/12개월/80/3,840` 잔존) 결함을, **임의 임계 의존 없는 구조 신호**로 근본수정. 최종 `output/20260604/별지3호.pdf` (T66 데이터 전부 빈칸, 분류축 라벨 보존).

**근본 원인**: 집 라운드 `ca4a963`의 terminator-table "example 셀만 비움(라벨 보존)" 정책이, 비목 배분표 라벨 보존하려다 인건비 명세표의 데이터값(대표·3,840)을 비목 라벨로 오인 보존 → 같은 example 행이 셀별로 분류 갈림. "300,000"처럼 더미패턴인 건 example로 잡히고 "대표·12개월"처럼 평범한 값은 label_or_content로 샘.

**수정 (`extract_hwpx_form.py` + `system_defaults.yaml`, md 0줄):**
- **"행 전체 vs example 셀만" 이분법 폐기 → 셀별 데이터열 신호**(`data_column_clear`): example 패턴 셀 + *헤더 이후 빈칸 있는 데이터 입력 열*의 비병합 셀 비움, 병합 분류축 라벨·빈칸없는 골격 열 보존.
- **큰표/작은표 판정 = `max_ex=3` 임의 임계 → 세로 병합(rowspan>1) 분류축 유무 구조 신호**(`has_merged_axis`). 9표 무손실 교체, 임계·example 개수 의존 0. 예시 인력 3명이든 4명이든 동일 동작.
- caption(단위표기 등 1셀 행)≠헤더 버그픽스(`header_min_cells=2`).

**검증**: T66 9셀 데이터 비움(시각+정량) · T43 실적표·T63/T64 헤더 회귀 0 · cross-form(F16PBU·민군 구/신 extract 비교) 변화 0 · 정량(확인필요 10·OOO 21·28.571·서술체 0) 동일. T64 집행시기 예시날짜도 비워짐(더미 제거 개선, 헤더 보존).

**⚠️ 미증명 (정직)**: 같은 구조(terminator fillable-list)를 가진 *다른* 양식에서의 양성 검증 미완 — 이 구조가 농식품 양식에만 있어 외부 cross-form은 "영향 0"으로만 증명됨. **다른 R&D 양식 확보 시 "분류축 라벨 보존 + 데이터 예시값 비움" 양성 검증 필요** (B 작업 재개 조건과 동일). 사용자가 "다른 R&D 양식 확보 후 검증" 결정(2026-06-04). 웹 자동다운로드는 정부사이트 세션차단으로 실패 → 양식은 사용자 제공 필요.

---

## (이전) 라운드 (2026-06-04 저녁) — 요약표 누락·오배치 + 단독신청 일괄

**한 줄 결과**: 사용자 지적("단독인데 협업·컨소시엄 셀 남음, 추진전략 등 미채움, 전체 파악 부족") 근본 수정. **최종 산출물 `output/20260604/별지3호.pdf`** (추진전략·목표시장·실현가능성 채움 · 협업/컨소 해당없음 · 라벨 회사명 오배치 5건 제거 · 회귀 0).

**근본 원인 (2곳, 지능 아니라 구조)**:
1. **PY 오분류** — T18 요약표 입력칸(추진전략·목표시장·실현가능성·협업)이 `※` 시작인데 `INSTRUCTION_PLACEHOLDER_RE`(80자·끝위치·단일※)에 안 맞아 `instruction` → `fill_targets` 제외 → proposal-writer 가 *제시조차 못 받음*. (proposal-writer.md:192 는 이미 "다중셀 표 instruction_placeholder=입력칸" 규정 — 정책 맞고 분류 틀림.)
2. **md 정책 부재** — 단독신청 전역 전파·라벨 오배치 방지·완료 자기검증 규칙 없음.

**수정 (PY 1 + yaml 1 + md 1)**:
- `extract_hwpx_form.py` `build_table` — **다중 셀 표(셀≥임계) 안 `instruction` → `instruction_placeholder` 승격** (1×1 standalone 안내박스는 유지). 표 크기 신호 = md:192 정책과 일치. 정본 `system_defaults.yaml hwpx_fill.instruction_placeholder_min_table_cells: 2`.
- `proposal-writer.md` — ① 단독신청 시 컨소시엄/참여기업/협업 *어휘* 셀 일괄 "해당 없음"(양식 전수, 셀 id 하드코딩 금지) ② 라벨(label_or_content) 셀 값 오배치 금지 ③ 완료 자기검증(미채움 0·컨소 모순 0·라벨 오배치 0).

**오배치 제거 (기존 fills 누적 결함 5건)**: 라벨/비목/집행시기/서명 셀에 "주식회사 다비오" 박힘 — T18_R7_C0(추진전략 라벨)·T43_R0_C1(주요역량)·T62_R2_C3·T63_R2_C2(비목 재료비)·T64_R13_C5(집행시기). 별지3호 5건 제거 → 비목 라벨 복원. (오탐 제외: T61 총괄표·T7/10/14 홍길동→대표자 = 의미일치 정당.)

**Cross-form**: PY 분류 변경이 실제 양식(mingun·F16PBU×2) 영향 **0** (다중셀 ※ 없음). RFP 문서(피지컬+1·방산+6)는 채움 대상 아님. 농식품만 입력칸 12개 정상 포함.

**재생성**: extract 재실행 → proposal-writer *타겟 재호출*(`output/20260604/fills_patch.yaml` 11셀: T18 서술 3 + 협업 해당없음 + 성과목표 6 + 오배치 삭제) → fills_total 병합(498) → 빌드.

**검증**: 추진전략/목표시장/실현가능성 ❍3-tier 채움 · 협업="해당없음" · 참여기업표 헤더 복원 · OOO 21 · 28.571억 · 비목더미 0 · 회귀 0.

**추가 수정 (fill_company 라벨 오매칭 — 일반 빌더 결함)**: 전수 검증 결과 별지3호=결함0 확인. 남은 결함은 *fill_company_cells.py 가 left hint 만 보고 라벨 셀("사업책임자"·"이름"·"서명" 등)을 회사정보 값자리로 오매칭*(별지밖에서 드러남). 일반 수정:
- `system_defaults.yaml` EXAMPLE_RE 에 **표준 예시 인명 `홍\s*길\s*[동순]`** 추가 (○○마트처럼 보편 더미) → "홍길동"=example(값자리), "사업책임자"=label(라벨) 구분.
- `fill_company_cells.py` — field 매칭 후 **`_is_fillable`(empty/example/example_row 만) 적용** → label_or_content 라벨 셀 채움 차단.
- cross-form: 농식품 라벨 오매칭(T3/T5/T85/T84) 제거 + "홍길동"→대표자 유지. mingun/f16gye 손실 전부 라벨 오매칭(값="(미확인)" 무의미) 제거 = **정당 매칭 손실 0**. 별지3호 회귀 0.

**미결 (사용자 결정)**:
- **투자유치·국내매출 목표수치 = `(확인 필요)` 유지** (2026-06-04 사용자 확정 — KB 미확정, 제출 직전 실값). 수출=10억(KB). T17↔T52 동일.
- **별지 밖 잔존**: fills_total 의 별지밖 라벨 오매칭(T3/T5/T85)은 *fill_company 재실행 시 자동 제거*(코드 근본 수정됨) — focus 별지3호라 fills_total 직접 미정리. T2(중소기업여부)·T10(참여기업명) 의미 오매칭/단독신청은 별지밖 + 별도 성격. 별지 밖 산출 시 정리.

---

## (이전) 라운드 (2026-06-04 오후) — C 확인 + D 검정제출본 + B 사전작업

**한 줄 결과**: 사용자 "B,C,D 다 해라" 처리. **C = 이미 해결 확인**(코드 0), **D = 검정 제출본 옵션 완성**(커밋 7677e79), **B = overfit 없는 사전작업만**(어휘+인식, 배치는 양식 대기).

**C 별지 분할 마커** — `167413f` 의 "단락 시작부 가드"(`SECTION_MARKER_MAX_START=4`)가 이미 작동. `[별지 4]` 문장중 참조(T60_R0_C0, 시작위치≈15 > 4)는 정확히 제외, 별지 제3호 7장 포함. F16PBU `[별지 제N호 서식]`·`붙임N` 도 정확 분리. **추가 코드 불필요.**

**D 검정 제출본** (커밋 `7677e79`) — 녹색(#00AA00) 채움색을 yaml(`system_defaults.hwpx_fill.filled_text_color`) 정본화 + `add_green_char_style(header, color)` 색 인자화 + `fill_hwpx(text_color=)` + **CLI `--submit`(검정 #000000)/`--color #RRGGBB`**. 기본=검토용 녹색 유지(회귀 0). cross-form F16PBU 검증(green/black). 제출 시점에만 `--submit`.

**B 비목 배치 — 사전작업만 (배치는 양식 확보 후)**:
- **차단 사유 (조사로 재확인)**: 비목별 표가 *다축 병합 구조*(비목=열, 재원/형태/주체=병합 행그룹)라 인접 라벨(hints)로 셀 식별 불가. 정교한 배치는 농식품 단일 양식에 fit → overfit. **검증 양식도 농식품 1개뿐** (F16PBU·피지컬AI·방산·민군 전부 비목별 표 없음 확인). 사용자 결정 = **"다른 R&D 양식 제공"** 후 cross-form 배치 구축.
- **완료한 overfit-0 사전작업**: ① `templates/budget_vocab.yaml` 에 `item_roles`(인건비/재료비/시설장비비/용역비/위탁/간접비/회계정산비 등 표준 R&D 비목) + `detail_axes`(fund/form/org/aggregate 구분 어휘). ② `scripts/fill_budget_cells.py` `find_detail_tables()` = 비목별 표 *일반 인식*(terminator + 비목어휘≥2 + 재원어휘≥1, 셀 id 0). ③ CLI `--detect-detail` 검증 모드.
- **인식 cross-form 검증**: 농식품 T62/63/64 정확 인식, 타 5양식(F16PBU×2·민군·피지컬AI·방산) 전부 **0** (false positive 0).

**👉 다음 세션 B 재개 조건**: *비목별 사업비 표를 가진 다른 정부 R&D 양식 1~2개* 를 `samples/rfp_downloaded/` 에 확보. 그 후 ① `find_detail_tables` 로 두 양식 인식 확인 → ② 명세 스키마(`--budget-detail` yaml: 비목→{국고,자부담_현금,자부담_현물}) 확정 → ③ 라벨·행그룹 기반 배치 + 소계/합계, *두 양식 공통 신호로만* 구현.

---

## (이전) 라운드 (2026-06-04 오전) — 사업비 비목별 표 더미 비움 일반화

**한 줄 결과**: 비목별 표(T62 자부담뷰·T63 국고뷰·T64 통합뷰·T66 인건비)의 *양식 더미값*(재료비 300,000·DMD소켓 등)이 최종본에 잔존하던 문제를 *일반 신호(terminator)* 로 근본 수정. **비목 라벨(재료비/인건비/시설장비비) 보존 + 금액·산출근거 더미만 비움.** 최종 산출물 `output/20260604/별지3호.pdf`.

**이번 라운드 변경 (코드 1 + yaml 1, 전부 일반·cross-form 검증):**
- `scripts/extract_hwpx_form.py` `_classify_example_rows` — terminator(`···`) 보유 표 = *fillable-list 확정 신호*. 그런 표에 한해 ① `max_example_rows` 가드 면제 ② 후보를 표 끝까지 확장(반복 블록·다단 포함) ③ **후보 행 수로 마킹 방식 결정**: 작은 예시행 표(≤max_ex)는 *행 전체* 비움(기존), 큰 항목 나열 표(>max_ex, 비목별)는 *example 셀만* 비움(라벨 보존). terminator 없는 표는 기존 로직 *완전 유지*.
- `templates/system_defaults.yaml` `example_row_detection` — `terminator_exempts_row_cap`·`mark_only_example_cells_in_terminator_table` 플래그 (정본 정책).

**핵심 일반 신호 (검증)**: terminator 보유 = fillable-list, 미보유 = 안내·기준표(T17 총괄·T76 단가기준·T75 집행안내·T60/65/67/68 ※안내). terminator가 "더미 채울 행" vs "양식이 주는 정보"를 가르는 일반 판별자. 셀 id·표번호·비목명 하드코딩 0.

**Cross-form 검증 (사용자 3회 강조 "overfit 금지"에 대한 직접 응답)**:
- mingun·F16PBU_계약·F16PBU_규격 양식 = **변경 0셀** (ellipsis 보유표 0 → blast radius 밖).
- T43/46/47/48/49 작은 예시행 표 = **회귀 0** (데이터 행 전체가 example라 행전체/example셀만 동일 결과).
- nongsik 변경 75셀 = T62/T63/T64/T66 *만*.

**검증 기준 충족**: 비목더미 0 · 비목라벨 유지 · OOO 21 · KORINDO 17 · 28.571억 · (확인 필요) 6(T36장비4 줄바꿈렌더 "(확인 \n필요)" + T46/47매출2) · (미확인) 1(법인등록번호).

**중요 함정 기록**: PDF text 의 "(확인 필요)" 는 `(확인 \n필요)` 로 줄바꿈 렌더될 수 있음 → `count('확인 필요')` 로 세면 누락. 정규식 `확인\s*필요` 로 검증할 것.

**(B) 비목 명세 배치 엔진 — 연기 결정 (사용자 2026-06-04)**: 비목 금액 미확정 + 양식별 3뷰(자부담/국고/통합) 구조라 *합성 데이터로 지금 만들면 현재 양식·합성값에 overfit*. 실제 비목 예산 확정 시 그 양식 구조에 맞춰 구현하기로 연기. (A) 더미 비움으로 비목 표는 "라벨+빈칸" 정상 상태.

---

## (이전) 라운드 (2026-06-02) — 문체 정본 근본수정 + PII 익명화 md정책

**한 줄 결과**: 문체(명사형 종결) 불일치의 *근본 원인 = 정본 SKILL.md 내부 모순* 을 제거하고, PII 익명화를 *py 키워드 하드코딩 대신 md 정책(§5-1)* 으로 구현. 별지3호를 명사형·OOO 로 재생성. **최종 산출물 `output/20260602/별지3호_최종.pdf`** (검증: 본문 서술체 0 · OOO 21 · 양식더미 0 · KORINDO 17 · 예산 28.571억).

**이번 라운드 변경 (전부 md = 정책. scripts/yaml 0줄):**
- `proposal-korean-style/SKILL.md` — **문체 정본 모순 제거**. 「기본 톤=당사는~합니다」(L12)가 「명사형 종결 우세」(L21)와 충돌 → 에이전트가 본문을 서술체로 쓰고 명사형 변환 2-step 필요 → 변환 누락 재발. **격식(정중함) ≠ 종결형(명사형)** 으로 분리, *본문 평서문 = 명사형 "~함/~임" 기본* 명시. 변환 단계 자체가 불필요해짐.
- `proposal-writer.md` — ① 문체 명사형 네이티브 생성 명시 ② **§5-1 PII 익명화 정책 신규**. *양식 컬럼 헤더 의미로* 개인 식별자(성명·성별·학교·전공·취득년도·채용년월 등) 판별 → `OOO`. 직위·학위·담당·참여율·경력은 보존. **셀id·키워드 하드코딩 금지, 헤더 의미로 판단** (임의 인력표 일반 적용). `OOO`(익명·제출시 실명) ≠ `(확인 필요)`(값 모름).
- `CLAUDE.md` — 문체 정본 포인터 일치.

**핵심 교훈 (사용자 directive)**: 판단·정책(문체·PII)은 **md 에**. py 키워드 리스트·yaml 매핑은 overfit. 처음에 PII 키워드를 py 에 박으려다 사용자가 잡음 → md 정책 + 에이전트가 양식 헤더 의미로 판별로 전환. 결과가 v7 검증본(OOO 21)과 정확히 일치 → 정책 정당성 교차증명.

**재생성 방식**: proposal-writer 에이전트 2회 — ① 명사형 정규화(서술체 본문→명사형, content_extra T18 포함 본문 서술체 0), ② §5-1 PII 익명화(인력표 확인필요→OOO 21). 내용·수치·id·순서 동결, 종결어미/PII값만 변경.

**서술 셀 구조 일관 (추가 수정)**: 요약표 "설명"(T18_R2_C2, content_extra 출처)이 평문 한 단락 — 형제 셀(상용화 배경 R5·확산계획 R10)은 ❍ 3-tier인데 혼자 평문. 전수 스캔으로 *진짜 위반 1건만* 확정(T38·T41 등 단일진술 셀은 평문 정당). ❍ 3-tier로 재구성(내용·명사형 보존). 근본: content_extra가 §3-tier 정책 우회 → **proposal-writer.md 에 "문체·구조는 fills 소스 불문 동일, 보충파일 면제 없음" 일반규칙 추가**.

**이미지 자동채움 — 텍스트 게이트 + 비전 검증 게이트 (일반 기능)**: 요약표 "이미지" 셀에 설명-매칭 KB 이미지 자동삽입 기능. 핵심 통찰 = `index.yaml`의 context_text는 *이미지 내용*이 아니라 *출처 슬라이드 텍스트* → 텍스트만으론 오삽입(image85 = 'AI기술' 슬라이드에서 추출된 *도심 위성사진*이 정밀농업 설명에 통과). **2단 게이트 구축**: ① 텍스트 관련성(`index_min_score`, 설명토큰 겹침 ≥ 임계, 실내지도 2<3 차단) ② 비전 검증(추출이미지는 LLM이 이미지 보고 설명과 일치 판정 통과해야 삽입; 큐레이트는 신뢰·면제). 부적합/미검증 → **빈칸 유지**(오삽입 < 빈칸).

**비전 검증 자동화 + gen-AI fallback 완성** (둘 다 구축·테스트):
- **비전 자동화**: 빌더가 내용불확실 후보(추출·생성)를 `<out>.image_review.yaml` 로 emit → *비전 서브에이전트*가 이미지를 실제로 보고 `vision_approved: <경로>|false` 판정(자율) → 재빌드 시 승인분만 삽입. 실증: 후보(객체탐지 앱 스크린샷)를 에이전트가 "도메인 맞지만 UI 노출 → 격식 부적합" 거부.
- **gen-AI fallback**: KB 텍스트게이트 None(적합 이미지 전무) → 설명을 프롬프트로 생성. 생성물도 비전 검증 대상. **실제 생성기 = 사내 Gemini/Imagen 연결**(`scripts/gen_image.py`, `generation.command` 배선, `enabled:true`). 키는 env `GEMINI_API_KEY` 에서만(커밋 0), 모델 `GEN_IMAGE_MODEL` env 교체(imagen-3.0-generate-002 / gemini-2.5-flash-image-preview). `generation.prompt_prefix` 로 격식 제안서 스타일 유도. **사용 전 준비: `pip install google-genai pillow` + `GEMINI_API_KEY` 설정** — 미설정 시 빈칸 graceful(검증됨, 크래시 0). 실제 생성 테스트는 키 보유자(사용자)가 수행: `python scripts/gen_image.py --out /tmp/t.png --prompt "..."`.
- **내용 기반 선택(파일명 무관)**: 사람이 넣은/생성 이미지를 *비전 캡션 인덱스*(`images/index.yaml`, content_text=비전이 이미지 보고 만든 내용묘사)로 검색. `_search_index_image`가 루트 `images/index.yaml`(내용) + `extracted/index.yaml`(슬라이드텍스트) 둘 다 검색. 실증: 의미없는 파일명(`Gemini_Generated_Image_n9vy...png`)을 정밀농업 설명이 *내용으로* 정확히 선택, 아키텍처 설명은 dsi_architecture, 무관설명은 빈칸(변별).
- 분류: py(게이트·`meaningful_tokens`·`_is_curated_image`·`generate_image`·내용인덱스검색·emission)·yaml(`index_min_score:3`·`use_weak_fallback:false`·`require_vision_approval_for_extracted:true`·`generation`)·md(proposal-writer §5-2). 비전 캡션은 서브에이전트가 이미지 보고 작성.
- **dabeeo+정밀농업 = KB에 시각적합 이미지 없음 → 빈칸**(사용자 결정; 게이트가 후보를 비전대기/거부로 정확히 보류). 임의 회사/RFP 공통, 특정 셀·이미지·모델 하드코딩 0.

**잔존 확인필요 6건 = 일반정책대로 `(확인 필요)` 확정** (비-PII 미확정 수치): 장비 단가 4(T36)·매출액 2(T46/T47). §5 정책(KB 미수록 값 → 확인필요)이 이미 규정하는 케이스 — v6의 `비움`은 *이 케이스만의 overfit*이라 폐기. 빈 셀은 0·누락 오인 + 양식 정합성 훼손. **§5에 "미확정 수치 비우지 말고 일관되게 확인필요" 일반규칙 명시** (특정 표만 비우는 예외 금지). 제출 직전 실값 교체.

---

## (이전) 라운드 (2026-06-01 저녁) — RFP 표 파싱 + 정성 근본수정

**한 줄 결과**: RFP 분석이 표를 버리는 .txt 를 써서 요건(성과목표 정성 등)을 놓치던 **상류 결함 발견·수정**. 표 보존 재분석(v2) → proposal 재생성(v7) → 정성 셀 RFP 가이드대로 채움. **최종 산출물 `output/20260601/별지3호_v7.pdf`**.

**이번 라운드 commit (5건, 전부 일반·cross-form 검증):**
- `ebb3a9f` RFP 파싱 표 보존 강제 (rfp-analyst.md + rfp.md + extract_proposal.py 표유실 가드). 공고 표 108개 `<표>` 유실 → 표보존 추출(36,110자)로 복원.
- `2e7a283` proposal-writer 규칙 7: 한 셀 base/_P fill 모순·중복 금지.
- `e674a4c` set_cell_text = 셀 전체 교체 (다단락 양식예시 잔존 차단) + fill_budget_cells base→_P0/_P1.
- (이전) `167413f` 별지 분할 마커 시작부 가드 · `8c8b5a3` 사업비 총괄 빌더 · `3f030a7` 매처 본사⊂본사업.

**정성 근본원인 체인**: ① 공고 표 유실 → 분석에 RFP 정성 가이드 없음 → ② proposal-writer 가 정성을 양식예시+우리내용 *모순 fills*(base full + _P 부분)로 냄 → ③ set_cell_text 가 base 첫단락만 채워 양식예시(0명·0건) 잔존. 셋 다 일반 수정. **결과: 정성 양식예시 잔존 0, RFP 가이드(역량강화·불량률·현안해결) 기반 다비오 정성 4항목.**

**재분석 산출물**: `rfp_analysis_v2.yaml`(성과목표 정량/정성 분리·지원과제분류·비목8종·평가17항목 복원), `fills_본체별지3_v7.yaml`(396, 규칙7 준수), `fills_total_v7.yaml`(476, 결정 적용).

---

## (이전) 라운드 (2026-06-01 오후) — 확인필요 27건 + 매처

**commit**: `c5a00eb` 기반.

**한 줄 결과**: A안 "확인 필요" 27건 사용자 결정 반영. v6 별지 제3호 PDF 재현.

**확인필요 27건 처리 결정** (사용자 확정 2026-06-01):
- ① 장비 단가 4건 (T36_R{1..4}_C5) → **비움**(삭제, 추후 견적)
- ② 참여 인력 PII 21건 (T41 성명·성별·학교·전공·취득년도·채용년월) → **OOO 익명** (직위·학위·담당·참여율·경력은 보존)
- ③ 해외계약·수출 매출액 2건 (T46_R2_C3, T47_R2_C1) → **비움**

**검증**: PDF 텍스트 `확인 필요` 0 · 양식 더미 0 · OOO 21 · 실적 보존(KORINDO·4개국·해외특허·투자 369억) · "해당 없음"(단독) 3.

**핵심 산출물**: `output/20260601/별지3호_v6.pdf` (19p). 중간물: `fills_total_v6.yaml`(472 명세, 결정 적용본), `fills_content_extra_v6.yaml`(참여율·솔루션설명 콘텐츠), `통합양식.form.yaml`(v6 재추출, example_row 84).

**🔧 일반 코드 수정 (이번 라운드 핵심 — `scripts/fill_company_cells.py`)**: 회사메타 매처의 2가지 일반 결함 수정.
- ① **keyword 부분매칭을 공백 토큰 경계 내로 제한** (`_tokenize`). 기존 `normalize()`가 공백을 다 지워 `"본사"`(HQ keyword)가 `"본 사업"`(→본사업)에 substring 오매칭 → *모든 한국 RFP*의 빈 셀이 회사주소로 오염되던 버그. 토큰 안 매칭만 허용 ("본사 소재지"·"본사소재지" 정당 케이스 유지).
- ② **비-fillable 셀(instruction_placeholder·checkbox 등) 채움 금지** (136행 `pass`→`continue`). 긴 안내문 속 "연락처"·"본사"가 ※박스·체크 셀을 오염시키던 것 차단.
- **cross-form 검증**: 농식품AI 44→29 매칭(정당 22 + 법인번호 등 미확인 7, spurious 15 제거), F16PBU규격 3→0(전부 spurious), F16PBU계약 checkbox 오매칭 제거+회사명/대표자 정당매칭 복원, 민군 정당 1. *정당 매칭 손실 0.*

**📌 범위 밖 (미확인) 3건 중 2건 처리** (사용자 "법인등록번호 빼고 처리"): 둘 다 위 매처버그가 원인이었음 →
- 인력1(책임자) **참여율** → 매처에서 정상 제외 후 콘텐츠 `100%`(표준 가정, 80/40/30%와 동일 방법론).
- 상용화 **솔루션 설명**(T18_R2_C2, ※설명박스) → 매처 제외 후 KB 기반 설명 콘텐츠.
- **법인등록번호** = `(미확인)` 유지 (사용자 지정, KB 미제공).

**중요 정정**: SESSION 이전 버전이 적은 "T62 자기부담금 / T66 참여인력" 표번호는 **부정확**. 실제 확인필요 셀은 모두 별지 제3호 내 **T36(장비)·T41(인력)·T46/T47(수출)**. T62/T66은 v6 form에 그 의미로 존재하지 않음. 표번호로 셀 식별 금지 — 의미/섹션으로.

**유실 무관 확인**: `fills_example_row_v6.yaml`(과거 39셀)은 디스크·메모리에 없으나, 해당 example_row(별지3호 22셀)는 전부 양식 더미(○○마트·○개국 등)이고 실데이터는 v5본문 R2 행에 이미 있음 → 자동 비움으로 충분. 에이전트 재생성 불필요.

---

## 다음 작업 후보 (사용자 결정 대기)

다음 세션에서 사용자가 "이어서 진행해줘" 라고 하면 → **아래 후보 제시 + 어디 갈지 묻기**. 임의 선택 금지.

- **A 완료** ✅ 확인필요 27건 + 범위밖 미확인 2건(참여율·설명) 처리, 매처 일반버그 수정.
  - 남은 미결: **법인등록번호 `(미확인)`** 1건 — KB 미제공.
- **사업비 총괄 자동화 완료** ✅ `fill_budget_cells.py` + `budget_vocab.yaml` (어휘 기반, 4양식 false-positive 0). 커밋 `8c8b5a3`.
  7-1 총괄표(국고 20억/자부담 8.571/현금 0.857/현물 7.714/총 28.571억) RFP 비율로 결정적 채움. 재현: `python scripts/fill_budget_cells.py <form> <rfp_analysis> <out> --gov-eok 20 --type 타입1`.
- **별지 분할 버그 수정 완료** ✅ `section_marker_max_start`(yaml 정본) — 마커가 단락 시작부일 때만 섹션 경계. 커밋 `167413f`.
  7장 사업비가 별지 제3호에서 잘못 분리되던 것 → **별지 제3호에 정상 포함**. cross-form(F16PBU·민군) 검증.
- **최종 산출물**: `output/20260601/별지3호_v6_최종.pdf` (7장 사업비 포함, 928KB). 검증: 확인필요 0·더미 0·OOO 21·미확인 1(법인등록번호만)·7장 총괄 28.571억.
- **비목별 표 더미 비움 완료** ✅ (2026-06-04) terminator 기반 일반화. T62/63/64/66 더미 0, 비목 라벨 유지, cross-form 3양식 변경 0. 커밋 예정.
- **다음 후보**:
  - **B (비목 명세 배치 엔진)** — *연기됨*. 실제 비목별 국고/자부담 금액이 확정되면, 그 양식 구조(자부담뷰/국고뷰/통합뷰)에 맞춰 명세→결정적 배치 + 소계/합계 자동. *전제*: 사용자 비목 예산 확정 (가정 금지). 지금 합성으로 만들면 overfit이라 연기.
  - **C 분할 버그** — 7장이 양식 안 "[별지 4]" 문구 때문에 별지 제3호에서 잘못 분리됨. split_hwpx 별지 마커 인식 정밀화 (마커가 셀/단락 *제목*인지, 문장 중 참조인지 구분).
  - **D T66 인건비 상세** — 사용자 결정 "비움" (인사 확정 후). (단 양식 더미는 이번 라운드에 비워짐.)
- **B** T62-류 multi-block 표 (한 표 안 여러 example 블록) 일반화 — 별지4 등 부속(현재 focus 밖)
- **C** v6 페이지별 전수 시각 검토 — 19p 중 인력(p12)·판로(p10) 확인됨, 나머지 미검
- **D** 검은색 제출본 출력 (녹색 디버그 → 검정) — 발주처 실제 제출 시점
- **E** 사용자 명시 다른 작업

---

## 비즈니스 결정 (사용자 확정 — 임의 변경 금지)

- **컨소시엄**: 단독신청 → ☑ 부 + 참여기업 "해당 없음"
- **신청유형**: 타입 1 (계약일로부터 1년 내 상용화)
- **사업비**: 총 28.6억 (자기부담 8.6 / 국고 20, 70:30)
- **제품명**: Eartheye Plantation — AI 기반 위성·드론·모바일 통합 정밀농업 솔루션
- **참여인력 PII**: ☑ `OOO` 익명 (성명·성별·학교·전공·취득년도·채용년월). 직위·학위·담당·참여율·경력은 실명/실값 보존. 발주처 제출 직전에만 실명. (2026-06-02 사용자 재확정)

이 결정사항은 *이전 라운드 사용자 확정*. 다음 라운드에서 변경하려면 사용자 명시 동의 필요.

---

## 재현 명령 (다른 PC / 산출물 재생성 시)

산출물은 `output/**` gitignore. 재현 흐름:

```bash
# 0. .hwp → .hwpx (한컴 COM 1회, Windows + 한컴오피스 필요)
#    이미 output/20260531/농식품AI_양식.hwpx 가 있으면 스킵
python scripts/hwp_to_hwpx.py \
    "samples/rfp_downloaded/[양식] 농식품 분야 「AI 응용제품 신속상용화 지원사업」.hwp" \
    "output/20260531/농식품AI_양식.hwpx"

# 1. 양식 분석 (example_row intent 자동 인식)
python scripts/extract_hwpx_form.py "output/20260531/농식품AI_양식.hwpx" "output/20260601/통합양식.form.yaml"

# 2. 자동 채움 (회사메타 + 재무)
python scripts/fill_company_cells.py "output/20260601/통합양식.form.yaml" "kb/company/dabeeo/profile.yaml" "output/20260601/fills_profile.yaml"
python scripts/fill_finance_cells.py "output/20260601/통합양식.form.yaml" "kb/company/dabeeo/finance.yaml" "output/20260601/fills_finance.yaml"

# 3. agent 채움 (example_row 39셀 + 본문 단락) — LLM 재호출 필요 (proposal-writer agent)
#    또는 메모리에 있는 fills_본체별지3_v5.yaml + fills_example_row_v6.yaml 재사용

# 4. fills 병합 (우선순위: example_row > profile > finance > v5 본문)
python -c "
import yaml
files = ['output/20260601/fills_example_row_v6.yaml', 'output/20260601/fills_profile.yaml',
        'output/20260601/fills_finance.yaml', 'output/20260531/fills_본체별지3_v5.yaml']
seen, merged = set(), []
for p in files:
    for f in yaml.safe_load(open(p, encoding='utf-8'))['fills']:
        if f['id'] not in seen:
            seen.add(f['id']); merged.append(f)
yaml.dump({'fills': merged}, open('output/20260601/fills_total_v6.yaml', 'w', encoding='utf-8'), allow_unicode=True, sort_keys=False)
"

# 5. fill_hwpx — *4번째 인자 form.yaml 필수* (example_row 자동 비움 정책 활성)
python scripts/fill_hwpx_form.py \
    "output/20260531/농식품AI_양식.hwpx" \
    "output/20260601/fills_total_v6.yaml" \
    "output/20260601/농식품AI_v6.hwpx" \
    "output/20260601/통합양식.form.yaml"

# 6. 별지 분할 + PDF
python scripts/split_hwpx_by_section.py "output/20260601/농식품AI_v6.hwpx" "output/20260601/통합양식.form.yaml" "output/20260601/별지_v6"
python scripts/hwpx_to_pdf.py "output/20260601/별지_v6/05_[별지_제3호]_사업계획서.hwpx" "output/20260601/별지3호_v6.pdf"
python scripts/pdf_to_text.py "output/20260601/별지3호_v6.pdf" "output/20260601/별지3호_v6.txt"
```

### 20260602 최종본(문체 명사형 + PII 익명화) 재현 — *LLM 재호출 불필요*

`output/20260602/fills_*.yaml`·`통합양식.form.yaml` 가 **이제 git 추적**되므로(이 라운드에 커밋), 다른 PC 에서 git pull 후 에이전트 재호출 없이 fill 단계부터 바로 재현 가능. (이미지 셀은 KB 시각적합 이미지 없음 → 빈칸 유지가 정상; `fills_image.yaml` 는 빈 채움이라 결과 동일.)

```bash
python scripts/fill_hwpx_form.py "output/20260531/농식품AI_양식.hwpx" "output/20260602/fills_total.yaml" "output/20260602/농식품AI_최종.hwpx" "output/20260602/통합양식.form.yaml"
python scripts/split_hwpx_by_section.py "output/20260602/농식품AI_최종.hwpx" "output/20260602/통합양식.form.yaml" "output/20260602/별지_최종"
python scripts/hwpx_to_pdf.py "output/20260602/별지_최종/05_[별지_제3호]_사업계획서.hwpx" "output/20260602/별지3호_최종.pdf"
```
검증 기준: 본문 서술체 0 · OOO 21 · 양식더미 0 · KORINDO 17 · 예산 28.571억.

### 20260604 최종본(비목더미+요약표+오배치+단독신청+fill_company 누적) 재현 — *LLM 재호출 불필요*

**정본 fills = `output/20260604/fills_total.yaml`** (498셀, patch 병합 + 오배치 제거 반영, git 추적). form.yaml·fills_total·fills_patch 모두 추적되므로 다른 PC 는 git pull 후 *에이전트 재호출 없이* 아래로 PDF 재생성.

```bash
# (form.yaml 은 추적본 그대로 사용 가능. 코드 변경 검증하려면 재추출해 추적본과 일치 확인)
python scripts/extract_hwpx_form.py "output/20260531/농식품AI_양식.hwpx" "output/20260604/통합양식.form.yaml"
# 정본 fills(20260604) 로 빌드
python scripts/fill_hwpx_form.py "output/20260531/농식품AI_양식.hwpx" "output/20260604/fills_total.yaml" "output/20260604/농식품AI_최종.hwpx" "output/20260604/통합양식.form.yaml"
python scripts/split_hwpx_by_section.py "output/20260604/농식품AI_최종.hwpx" "output/20260604/통합양식.form.yaml" "output/20260604/별지_최종"
python scripts/hwpx_to_pdf.py "output/20260604/별지_최종/05_[별지_제3호]_사업계획서.hwpx" "output/20260604/별지3호.pdf"
python scripts/pdf_to_text.py "output/20260604/별지3호.pdf" "output/20260604/별지3호.txt"
# 제출본(검정) 필요 시: 위 fill_hwpx 에 --submit 추가
```
검증 기준: 비목더미(300,000·DMD소켓) 0 · 비목라벨(재료비·인건비·시설장비비) 유지 · **추진전략/목표시장/실현가능성 ❍채움** · **협업="해당 없음"** · 라벨 회사명 오배치 0 · OOO 21 · KORINDO 20 · 28.571억 · 정규식 `확인\s*필요` 10(장비4+매출2+투자/국내목표4) · 미확인 1.

### Cross-form 검증 재현 (일반성 보장)

```bash
# 변경 전후 form.yaml 의 셀 intent diff — terminator 미보유 양식은 변경 0 이어야.
python scripts/extract_hwpx_form.py "samples/rfp_downloaded/26년_민군규격표준화_제안서양식.hwpx" "/tmp/mingun.form.yaml"
python scripts/extract_hwpx_form.py "samples/rfp_downloaded/F16PBU_계약특수조건.hwpx" "/tmp/f16_gye.form.yaml"
# (Windows: python 의 / tmp 경로는 프로젝트 _work/ 권장 — git-bash /tmp 와 다름)
```

---

## 인수받은 Claude 행동 지침

세션 시작 시 (특히 "이어서 진행해줘" 받았을 때):

1. **이 파일과 CLAUDE.md 모두 인지 후 사용자에게 다음 작업 후보 4개 제시** — A/B/C/D 중 어디 갈지 묻기. 임의 진행 금지.
2. **비즈니스 결정사항 (위 4개) 임의 변경 금지** — 사용자가 명시적으로 바꾸지 않는 한 그대로 사용.
3. **CLAUDE.md 의 게이트·체크리스트 모두 적용** — 행동 전 일반성 게이트 4문항, 분류 체크리스트, 본체 별지만 산출, 양식 보존 원칙.
4. **메모리 폴더 (~/.claude/projects/.../memory/) 가 있으면 추가 컨텍스트로 사용**. 없으면 이 파일과 git log 만으로도 충분히 작업 가능.
5. **commit message + git log** 을 읽어 최근 변경 의도 파악. 특히 `git log --oneline -10` 으로 흐름 확인.

---

## 핵심 일반화 규칙 (이번 라운드 결과)

표 안 "fillable-list" 구조 자동 인식 + example 행 처리:

```
표마다 (extract_hwpx_form._classify_example_rows):
  rows >= 3 AND cols >= 2
  헤더 행 = 첫 *모든 셀 non-empty label_or_content* 행
  terminator = 행에 셀 1개 + ellipsis (···/.../…/·) 패턴
  is_fillable_list = (헤더 이후 빈 행 ≥ 1) OR terminator 존재
  ex_candidates = (헤더+1) ~ (첫 빈/terminator 이전) 비-empty 행
  ex_candidates 중 ≥1 셀 intent=example 필수 (false positive 차단)
  → 조건 충족 시 ex_candidates 셀 모두 example_row 마킹
  → terminator 셀 모두 table_terminator 마킹
```

빌더 처리:
- `fill_company_cells` / `fill_finance_cells`: `_is_fillable` 에 example_row 포함 (KB hint 매칭)
- `proposal-writer` agent: example_row 셀에 KB 인용 fills 작성. 모르면 `(확인 필요)` 또는 entry 생략
- `fill_hwpx_form`: CLI 4번째 인자 `[form.yaml]` 제공 시 fills 미매칭 example_row 자동 비움

yaml 정본: `templates/system_defaults.yaml` 의 `hwpx_fill.example_row_detection` + `auto_clear_unfilled_example_row`.

---

## 갱신 룰

이 SESSION.md 는:
- **큰 라운드 종료 시** (사용자 검증 통과 산출물이 나왔을 때)
- **commit + push 직전**
- **세션을 다른 PC로 넘길 때**

이 시점에 *다음 라운드 Claude가 필요한 최소 컨텍스트*로 업데이트 후 commit. 너무 상세히 적지 말고 *다음 작업 후보 + 비즈니스 결정 + 재현 명령* 위주.

상세 컨텍스트 (라운드별 일지·내부 의사결정 흐름)는 메모리 (`~/.claude/projects/.../memory/`) 에 남김.
