# 세션 인수인계 — DSI

> **이 파일은 git에 들어가는 *다음 세션 Claude를 위한 인수인계*다.**
> 매 큰 라운드 종료 시 / commit 직전 갱신. CLAUDE.md 룰에 따라 모든 세션 시작 시 *가장 먼저* 읽힘.
> 메모리(~/.claude/projects/.../memory/)는 PC별이라 동기화 마찰 있음 — 핵심 인계 정보는 *여기*에 둠.

---

## 마지막 라운드 (2026-06-01 오후)

**commit**: `c5a00eb` (코드 변경 없음 — 이번 라운드는 채움 결정·재현만)

**한 줄 결과**: A안 "확인 필요" 27건 사용자 결정 반영 완료. v6 별지 제3호 PDF 재현(WSL PC에서도 한컴 COM 정상).

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

- **A 완료** ✅ 확인필요 27건 + 범위밖 미확인 2건(참여율·설명) 처리, 매처 일반버그 수정 (위 마지막 라운드 참조).
  - 남은 미결: **법인등록번호 `(미확인)`** 1건 — KB 미제공, 사용자가 실제 등기번호 줘야 채움 (그 전엔 유지).
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
