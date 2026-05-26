---
name: session-20260526-progress
description: 회사 WSL 세션 2026-05-26 의 진단 결과·합의 — intent 분류·매핑 검증 결과·미완 작업
metadata: 
  node_type: memory
  type: project
  originSessionId: 6c490a2a-733b-43a9-96e8-d9e2cf641638
---

회사 WSL 세션 2026-05-26 합의:

**합의된 알고리즘 변경** (commit a6468ae, e82dca7):
- `CHECKBOX_RE = re.compile(r"[□☐☑☒✓✔■▣◧◨]")` — 체크박스 문자 포함 만으로 식별, 라벨 길이 무관, 한컴 변형 포함
- `EXAMPLE_RE` 에서 `↳` (↳) 제거 → `SUBORDINATE_RE` 가 처리. 한국 RFP 양식에서 ↳ 는 종속 항목 표시 (예시 아님)

**Why**: 신청유형 같은 *긴 라벨 + 괄호 체크박스* 셀이 기존 좁은 regex 로 식별 실패. ↳ 시작 셀이 example 로 잘못 분류되어 부속 항목 매핑 단서 손실.

**How to apply**: 다른 RFP 양식 분석 시에도 동일. 추가 패턴 박을 때 *한국 RFP 일반 관행* 인지 검증 후 (특정 RFP 만 트리거되면 overfit — [[feedback_no_overfit]]).

**검증된 데이터 사실** (집에서 PDF 시각 검증 보강 필요):
- 농식품AI 본체별지 셀 id 매핑 *완전 0 오차* (358 셀·54 단락·13 셀안단락 모두)
- 진짜 검토 셀 1건만 — T16_R2_C0 (단독 신청 시 "해당 없음" 명시 적합 여부)
- 집에서 "셀 매핑 오차" 라 한 건 *시각 어긋남* (fill_hwpx_form XML 편집 결함 또는 한컴 render 한계) — 회사에서 재현 불가

**관련**: [[feedback_intent_understanding]], [[feedback_no_overfit]], [[feedback_xml_fill]]
