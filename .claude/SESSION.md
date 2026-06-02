# 세션 인수인계 — DSI

> **이 파일은 git에 들어가는 *다음 세션 Claude를 위한 인수인계*다.**
> 매 큰 라운드 종료 시 / commit 직전 갱신. CLAUDE.md 룰에 따라 모든 세션 시작 시 *가장 먼저* 읽힘.
> 메모리(~/.claude/projects/.../memory/)는 PC별이라 동기화 마찰 있음 — 핵심 인계 정보는 *여기*에 둠.

---

## 마지막 라운드 (2026-06-02) — 문체 정본 근본수정 + PII 익명화 md정책

**한 줄 결과**: 문체(명사형 종결) 불일치의 *근본 원인 = 정본 SKILL.md 내부 모순* 을 제거하고, PII 익명화를 *py 키워드 하드코딩 대신 md 정책(§5-1)* 으로 구현. 별지3호를 명사형·OOO 로 재생성. **최종 산출물 `output/20260602/별지3호_최종.pdf`** (검증: 본문 서술체 0 · OOO 21 · 양식더미 0 · KORINDO 17 · 예산 28.571억).

**이번 라운드 변경 (전부 md = 정책. scripts/yaml 0줄):**
- `proposal-korean-style/SKILL.md` — **문체 정본 모순 제거**. 「기본 톤=당사는~합니다」(L12)가 「명사형 종결 우세」(L21)와 충돌 → 에이전트가 본문을 서술체로 쓰고 명사형 변환 2-step 필요 → 변환 누락 재발. **격식(정중함) ≠ 종결형(명사형)** 으로 분리, *본문 평서문 = 명사형 "~함/~임" 기본* 명시. 변환 단계 자체가 불필요해짐.
- `proposal-writer.md` — ① 문체 명사형 네이티브 생성 명시 ② **§5-1 PII 익명화 정책 신규**. *양식 컬럼 헤더 의미로* 개인 식별자(성명·성별·학교·전공·취득년도·채용년월 등) 판별 → `OOO`. 직위·학위·담당·참여율·경력은 보존. **셀id·키워드 하드코딩 금지, 헤더 의미로 판단** (임의 인력표 일반 적용). `OOO`(익명·제출시 실명) ≠ `(확인 필요)`(값 모름).
- `CLAUDE.md` — 문체 정본 포인터 일치.

**핵심 교훈 (사용자 directive)**: 판단·정책(문체·PII)은 **md 에**. py 키워드 리스트·yaml 매핑은 overfit. 처음에 PII 키워드를 py 에 박으려다 사용자가 잡음 → md 정책 + 에이전트가 양식 헤더 의미로 판별로 전환. 결과가 v7 검증본(OOO 21)과 정확히 일치 → 정책 정당성 교차증명.

**재생성 방식**: proposal-writer 에이전트 2회 — ① 명사형 정규화(서술체 본문→명사형, content_extra T18 포함 본문 서술체 0), ② §5-1 PII 익명화(인력표 확인필요→OOO 21). 내용·수치·id·순서 동결, 종결어미/PII값만 변경.

**서술 셀 구조 일관 (추가 수정)**: 요약표 "설명"(T18_R2_C2, content_extra 출처)이 평문 한 단락 — 형제 셀(상용화 배경 R5·확산계획 R10)은 ❍ 3-tier인데 혼자 평문. 전수 스캔으로 *진짜 위반 1건만* 확정(T38·T41 등 단일진술 셀은 평문 정당). ❍ 3-tier로 재구성(내용·명사형 보존). 근본: content_extra가 §3-tier 정책 우회 → **proposal-writer.md 에 "문체·구조는 fills 소스 불문 동일, 보충파일 면제 없음" 일반규칙 추가**.

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
- **다음 후보**:
  - **B (사업비 비목별, 2차)** — 7-2~7-4 비목별 배분(표준 R&D 비율 자동). *전제*: cross-form 검증용 다른 R&D 사업비 양식 1~2개 확보 (단일 양식 overfit 방지).
  - **C 분할 버그** — 7장이 양식 안 "[별지 4]" 문구 때문에 별지 제3호에서 잘못 분리됨. split_hwpx 별지 마커 인식 정밀화 (마커가 셀/단락 *제목*인지, 문장 중 참조인지 구분).
  - **D T66 인건비 상세** — 사용자 결정 "비움" (인사 확정 후).
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
