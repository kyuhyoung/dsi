---
name: green-text-must-be-optin
description: "채움 텍스트 강제 녹색(#00AA00)은 디버그 기능 — 제출 산출물엔 부적합, opt-in 전환 필요"
metadata: 
  node_type: memory
  type: project
  originSessionId: 582367a4-8673-48f1-a75f-d121aba04a1b
---

`fill_hwpx_form.py`의 `set_cell_text`/`set_paragraph_text`가 채운 텍스트를 *무조건* 녹색(`#00AA00`, `add_green_char_style`)으로 칠한다 — 검토 시 "AI가 채운 곳" 구분용 디버그 기능.

**문제**: (1) 실제 제출 산출물엔 검은 글자여야 함. (2) 검은 배경 입력 셀을 쓰는 양식(예: 26년 민군규격표준화)에선 녹색이 묻혀 가독성 저하. 현재 무조건 적용이라 양쪽 다 부적합.

**How to apply**: 녹색 강제를 *opt-in*으로 (기본 off → 원본 charPrIDRef 유지, `--mark-fills` 같은 검토 플래그로만 on). `set_cell_text`는 이미 녹색 off 시 원본 charPr 유지하도록 수정돼 있어, `add_green_char_style` 호출 자체를 플래그로 막으면 됨. 미완(2026-05-26 기준). 관련 [[linesegarray-fill-fix]], [[image-insertion-feature]].
