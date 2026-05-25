---
name: 양식 보존 원칙
description: 제안서 양식(.hwp/.hwpx/.docx)은 절대 만지지 않고, 빈 셀에 텍스트만 박는다. form_to_docx 같은 재구성 방식 금지.
type: feedback
originSessionId: 9831bd2c-c977-4c8a-b8a9-4b875d797ede
---
**원칙 (사용자 확정 2026-05-24)**: *"양식은 절대 만지지 않는다. 빈 셀에 텍스트만 박는다."*

**Why**: 근본 치유 1차·2차에서 양식 visual을 시스템이 재현하려고 시도 (extract_hwp_form의 visual 추출 + form_to_docx의 docx 재구성). 매번 미세 손실·1:1 보장 불가 문제 발생. 양식 자체가 *시각 정답의 단일 출처*. 시스템 책임은 *빈칸 채움뿐*.

**How to apply**:
- 양식 구조 추출은 *빈 셀 식별*과 *셀 의미 hint 부여* 목적으로만. visual·border·색·폰트 추출 코드 금지.
- 채움 출력은 *원본 양식 파일에 직접 박는 방식*만 사용:
  - `.hwp` → HwpObject COM (`scripts/fill_hwp_form.py`)
  - `.hwpx` → zip+XML 직접 편집
  - `.docx` → python-docx 셀 채움
- `form-analyst` agent, `form_to_docx.py`, style.yaml 의 cell visual 정의는 폐기 대상.
- 셀 식별자는 명시적으로: `T{table_idx}_R{row}_C{col}` 형식.
- proposal-writer 출력은 `fills: [{id, text}]` 명세만, visual·서식 지정 금지.
