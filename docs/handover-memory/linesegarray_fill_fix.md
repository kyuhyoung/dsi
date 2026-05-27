---
name: linesegarray-fill-fix
description: 채움 텍스트 한컴 겹침 렌더의 근본 원인·수정 — set_cell_text가 stale linesegarray 미삭제
metadata: 
  node_type: memory
  type: project
  originSessionId: 582367a4-8673-48f1-a75f-d121aba04a1b
---

HWPX 양식 채움 후 *긴 텍스트가 한컴에서 한 줄에 글자 겹쳐 렌더*되던 버그의 근본 원인과 수정 (2026-05-26).

**원인**: `fill_hwpx_form.py`의 `set_cell_text`가 셀 단락의 stale `<hp:linesegarray>`(줄 layout 캐시)를 안 지웠다. 짧은 placeholder 기준 단일 lineseg(`horzsize` 고정)에 긴 새 텍스트를 욱여넣어 한컴이 1줄에 겹쳐 렌더. `set_paragraph_text`(P-id 경로)는 이미 삭제하고 있었으나 `set_cell_text`(T-id 셀 경로)만 누락.

**수정**: `set_cell_text`를 `set_paragraph_text`와 동일 원칙으로 — 기존 run 전부 제거(placeholder 잔존 방지) + 새 run 1개 + `<hp:linesegarray>` 삭제(한컴이 열 때 재배치). 녹색 off 시 원본 charPrIDRef 유지.

**Why**: handover 문서가 "집/한컴 필요"로 남긴 미해결 갭 *"hp:t render 한계 / 셀 매핑 시각 어긋남"의 진짜 원인*이 이것이었다. v15 page8 전 셀 정상 줄바꿈으로 검증.

**How to apply**: HWPX XML로 단락 텍스트를 교체하는 *모든* 경로에서 linesegarray를 함께 삭제해야 한다 (일반 원칙, 양식 무관). 매직넘버 없음. 관련 [[image-insertion-feature]], [[feedback_xml_fill]].

**일반성 검증 (2개 양식)**: 농식품AI(흰 배경, v15 시각 확인) + 26년 민군규격표준화 양식(코드 수정 0, PDF 텍스트 추출로 5줄 정확 줄바꿈 확인). 민군은 *검은 배경*(원본도 동일 — 양식 본래)이라 고해상도 이미지로는 '흩어짐'처럼 착시됐으나, PDF 텍스트 추출 결과 내용·줄바꿈 정상. *교훈*: 렌더 이미지만으로 실패 단정 말 것 — PDF 텍스트 추출이 레이아웃 정오 판정에 결정적. 관련 [[green-text-must-be-optin]].
