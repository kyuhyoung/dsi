---
name: green-text-must-be-optin
description: "AI가 채운 셀 텍스트의 녹색(#00AA00)은 *의도된 디버그 표시* — 버그 아님, 제거·문제삼지 말 것"
metadata: 
  node_type: memory
  type: project
  originSessionId: 582367a4-8673-48f1-a75f-d121aba04a1b
---

`fill_hwpx_form.py`의 `set_cell_text`/`set_paragraph_text`가 채운 텍스트를 녹색(`#00AA00`, `add_green_char_style`)으로 칠하는 것은 **의도된 디버그·검토 장치**다 — 양식 원본 텍스트(검정) vs AI가 생성·채운 내용을 한눈에 구분하기 위함.

**버그가 아니다. 제거하거나 "검은색으로 고쳐야 한다 / opt-in 시켜야 한다"고 문제삼지 마라** — 클론한 다른 PC의 다른 Claude 포함.

**Why**: 한 세션에서 이걸 "제출 부적합 → opt-in 전환 필요"로 *잘못 분류*한 적 있음. 사용자 명시 정정: 작업·검토 단계는 녹색이 정상(설계 의도), 발주처 *실제 제출 시에만* 검은색 버전을 별도 생성(그 시점에 사용자가 결정·처리).

**How to apply**: 녹색 그대로 둔다. 검은색은 *최종 제출 단계의 별도 출력*이지 디폴트 변경이 아니다. 프로젝트 `.claude/CLAUDE.md` 의 "AI가 채운 셀 텍스트는 *녹색*" 절 참조. 관련 [[linesegarray-fill-fix]], [[image-insertion-feature]].
