# 세션 인수인계 — DSI

> **이 파일은 git에 들어가는 *다음 세션 Claude를 위한 인수인계*다.**
> 매 큰 라운드 종료 시 / commit 직전 갱신. CLAUDE.md 룰에 따라 모든 세션 시작 시 *가장 먼저* 읽힘.
> 메모리(~/.claude/projects/.../memory/)는 PC별이라 동기화 마찰 있음 — 핵심 인계 정보는 *여기*에 둠.

---

## 마지막 라운드 (2026-06-01)

**commit**: `c5a00eb` — 표 안 양식 예시 행 일반 처리 (example_row intent + 자동 비움)

**한 줄 결과**: 농식품AI 별지 제3호 잔존 placeholder 13건 → 0건. F16PBU·민군규격 등 4개 양식 cross-form 검증 통과.

**핵심 산출물**: `output/20260601/별지3호_v6.pdf` (재현 가능 — 산출물은 gitignore)

---

## 다음 작업 후보 (사용자 결정 대기)

다음 세션에서 사용자가 "이어서 진행해줘" 라고 하면 → **아래 후보 4개 제시 + 어디 갈지 묻기**. 임의 선택 금지.

- **A** (확인 필요) 16건 사용자 검토·확정
  - T46 (3) 국내 유통채널 진출 실적
  - T47_R1_C1 누적 수출액 금액
  - T62 (4) 자기부담금 8.6억 비목별 분배·산출근거
  - T66 (8) 참여 인력 PII (성명·직위·월급여·참여율·기존/신규·현금/현물·채용시기)
- **B** T62 multi-block 표 처리 — 한 표 안 여러 example 행 블록 (T62 R5/R8/R9 등) 일반화
- **C** v6 페이지별 시각 검토 — 새 표 셀 채움 정합성 (PDF text 우선)
- **D** 사용자 명시 다른 작업

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
