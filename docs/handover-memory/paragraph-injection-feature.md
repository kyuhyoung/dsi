---
name: paragraph-injection-feature
description: 빌더가 양식 placeholder 단락을 복제·주입해 서술 섹션을 N단락으로 풍부하게 — feedback_paragraph_fill 갭 해소
metadata: 
  node_type: memory
  type: project
  originSessionId: 582367a4-8673-48f1-a75f-d121aba04a1b
---

`fill_hwpx_form.py`의 **`inject_paragraphs()`** — 서술형 섹션(상용화 대상 소개 등)을 단 몇 줄이 아니라 *여러 단락*으로 채우는 핵심 기능 (2026-05-27 구현, [[feedback_paragraph_fill]] 미달 갭 해소).

**원리 (일반·하드코딩 0)**: 양식의 연속 placeholder 단락(❍/-/* 레벨)을 **레벨 템플릿으로 복제**해 N개 단락을 주입. 불릿·들여쓰기·paraPr 는 *양식 자체에서 학습*(복제), filler 패턴(가나다 등)만 `templates/system_defaults.yaml`의 `hwpx_fill.placeholder_filler_pattern`. 단락 추가로 top-level 인덱스가 변하므로 anchor 내림차순·다른 fill 이후 처리. linesegarray 삭제([[linesegarray-fill-fix]])·green([[green-text-must-be-optin]]) 적용.

**fills.yaml 스키마**: 단락 항목이 단일 `text` 대신 `paragraphs:` 리스트 (각 줄 '마커+내용', 마커는 양식의 ❍/-/* 그대로).
```yaml
- id: P55              # 섹션 첫 placeholder = anchor
  paragraphs:
    - '❍ 소제목'
    - '- 세부 내용'
    - '* 더 세부'
```

**How to apply**: proposal-writer 가 "분량 제한 없음/상세히" 류 섹션을 `paragraphs` 다단 구조(시장→필요성 As-Is/To-Be→개요→기능별 상세+정량→성숙도)로 풍부하게 작성하되 **KB 검증 사실만, 창작 금지**. 분할은 COM 매크로 말고 `split_hwpx_by_section.py`(XML, 결정적). 검증: hwpx_to_pdf(RPC 재시도 내장)→pdf_to_png/render_page_region.
