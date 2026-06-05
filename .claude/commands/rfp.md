---
description: RFP 공고와 채울 양식(.hwp/.hwpx)을 받아 → 분석 → 비즈니스 결정 확인 → 양식 자동채움(회사·재무·사업비) → 서술·실적 채움 → 제안서(.hwp/.pdf) 생성. 발표자료(.pptx)는 선택. 단계마다 검토.
---

# /rfp 명령 — HWP 양식 채움 제안서 자동 생성

## 사용법

```
/rfp <RFP 공고 파일> [채울 양식 파일(.hwp/.hwpx)]
```
- **양식 파일**: RFP에 동봉/별첨된 빈칸 양식. 주면 *양식 채움 모드*(이 문서), 없으면 자유 서술 `.docx` 모드(맨 끝 참조).
- 입력 포맷: `.hwp`/`.hwpx`/`.pdf`/`.docx`.

> 원칙: 양식은 *절대 만지지 않고* 빈 셀에 텍스트만 채운다([[feedback_form_principle]]). 회사·RFP·양식은 모두 변수 — 임의 조합에 코드 수정 0으로 동작.

---

## 흐름 (양식 채움 모드)

### 1. RFP 분석
- **표 보존 추출 (필수)**: `python scripts/extract_proposal.py <RFP> <공고.txt>` — 표 행·셀 보존(`<표>` placeholder 발견 시 재추출). 한국 RFP는 평가배점·자격·성과목표·예산비율이 *표 안*에 있음.
- `rfp-analyst` 에이전트 호출 → `rfp_analysis.yaml` (요건·평가·일정·예산). 예산 비율(국고/자부담·현금/현물)이 공고에 명시되면 추출, 없으면 생략(가정 금지).

### ✋ 검토 1: 분석 결과 — 누락·위험신호 강조. *진행* 대기.

### 2. 비즈니스 결정 확인 (한 번에 질문 — RFP·KB로 자동 안 되는 *사람 결정*)
분석 후, 채움 *전*에 아래를 **한 번에** 묻는다 (사용자가 한 답변으로 답):
1. **신청 형태** — 단독 / 컨소시엄(참여기업·역할)
2. **신청유형** — RFP에 유형 구분(예: 타입1/2)이 있으면 어느 것 (없으면 해당없음)
3. **사업비** — ① 총액(또는 국고 신청액) ② (매칭펀드형이면) 국고:자부담 비율 ③ 현금:현물 비율. *RFP에 명시돼 있으면 "RFP대로"*, 없으면 결정(미지정 시 `(확인 필요)`로 비움)
4. **제품·솔루션 공식명**
5. **참여인력 PII** — 실명 / `OOO` 익명(제출 직전 실명)

→ 답을 `output/<날짜>/decisions.yaml` 에 기록하고 이후 단계에 주입. (사업명·발주처·예산한도·배점·일정·요구사항은 RFP에서 자동 추출, 회사 실적·기술·인증은 KB에서 자동 인용 — 묻지 않음.)

### 3. 양식 준비
- `.hwp`면 변환(한컴, 1회): `python scripts/hwp_to_hwpx.py <양식> <양식.hwpx>`
- 양식 분석: `python scripts/extract_hwpx_form.py <양식.hwpx> <form.yaml>` (빈칸·라벨·example행·별지 구조 자동 인식)

### 4. 자동 채움 (회사메타·재무·사업비 — 결정적, LLM 불필요)
```
python scripts/fill_company_cells.py <form.yaml> kb/company/<회사>/profile.yaml <fills_profile.yaml>
python scripts/fill_finance_cells.py <form.yaml> kb/company/<회사>/finance.yaml <fills_finance.yaml>
python scripts/fill_budget_cells.py <form.yaml> <rfp_analysis.yaml> <fills_budget.yaml> \
    --gov-eok <국고억> --type <유형> [--self-pct <%> --cash-pct <%> --in-kind-pct <%>]
```
- 사업비 비율: RFP 명시 시 `rfp_analysis.yaml`에서 자동, 아니면 decisions의 비율을 CLI로 명시. *미지정 시 총괄표 `(확인 필요)`* (가정 금지, CLAUDE.md "명시 안 한 결정은 물어라").

### 5. 서술·실적·이미지 채움
- `proposal-writer` 에이전트 호출 → `fills_본체.yaml`
  - 서술 셀(추진전략·목표시장·실현가능성 등 ❍ 3-tier·명사형), example_row(인력·실적 KB 인용), 이미지 셀(상보/중복 판단·캡션·없으면 명세)
  - decisions 적용: 단독신청 전 섹션 일관(컨소/공동 모순 0), PII `OOO`, 제품명, 미확정 수치 `(확인 필요)`

### ✋ 검토 2: 채움 명세 — 문체·단독신청 일관·미채움 점검. *진행* 대기.

### 6. 빌드 → 제안서 hwp / pdf
```
# fills 병합 (본체 + profile + finance + budget; id 중복 제거)
python scripts/fill_hwpx_form.py <양식.hwpx> <fills_total.yaml> <채움.hwpx> <form.yaml>
python scripts/split_hwpx_by_section.py <채움.hwpx> <form.yaml> <별지폴더>
# 본체 별지(보통 사업계획서)만 PDF — CLAUDE.md 작업 포커스 별지 따름
python scripts/hwpx_to_pdf.py "<별지폴더>/<본체별지.hwpx>" <별지.pdf>
```
- 검토용은 채움 글자 *녹색*([[green-text-must-be-optin]]). 발주처 제출본은 `fill_hwpx_form ... --submit`(검정).

### 7. (선택) 발표자료 .pptx — RFP가 발표를 요구할 때만
- `ppt-designer` → `scripts/yaml_to_pptx.py` → `.pptx` + LibreOffice PDF + `visual-validator` 검증. (기존 PPT 흐름 — 발표 불요 시 스킵.)

### 8. 결과 보고
산출물 경로 정리: `decisions.yaml`·`rfp_analysis.yaml`·`form.yaml`·`fills_total.yaml`·`채움.hwpx`·`별지.pdf` (+ `.pptx` 선택).
- `.hwp` 입력이면: "한컴에서 채움.hwpx 열어 .hwp로 저장" 안내.

---

## 재현 (LLM 재호출 없이 — `fills_total.yaml`이 이미 있으면)
무거운 단계(양식 변환·rfp-analyst·proposal-writer)를 건너뛰고 **6단계 빌드만** → ~20초. (`fills_total.yaml`은 git 추적되므로 다른 PC에서도 동일 산출.)

## 무인 자동 모드 (옵션)
검토 지점(✋)을 스킵하고 1→8을 연쇄 실행. 비즈니스 결정은 `decisions.yaml`을 미리 주면 질문도 생략. 전체 ~15~20분(LLM 분석+본문이 대부분). *중간 검토를 못 하므로 새 양식엔 위험* — 검증된 양식·반복 작업에 권장.

## 검토 응답: `진행`/`다음`/`ok` · `수정: <내용>` · `중단`

## 에러 처리
| 상황 | 대응 |
|---|---|
| 양식 파일 없음 | 자유 서술 `.docx` 모드로 전환 (rfp-analyst → proposal-writer → docx skill → pptx) |
| 한컴 변환/PDF 실패 | 한컴 프로세스 정리 후 1회 재시도, 그래도 실패 시 오류 보고 |
| 비즈니스 결정 미입력 | 가정 금지 — 해당 셀 `(확인 필요)` + 사용자에게 재질의 |
| KB 검색 빈약 | 사용자 알림, 진행 여부 확인 |
| 검토 단계 *중단* | 현재까지 산출물만 저장하고 종료 |

## 출력 폴더
```
output/<YYYYMMDD>/
├── decisions.yaml          # 비즈니스 결정 (재현·무인용)
├── rfp_analysis.yaml       # rfp-analyst 결과
├── 통합양식.form.yaml      # 양식 분석
├── fills_total.yaml        # 채움 명세 (git 추적 — 재현 핵심)
├── <사업명>_채움.hwpx
└── 별지_<본체>.pdf
```
