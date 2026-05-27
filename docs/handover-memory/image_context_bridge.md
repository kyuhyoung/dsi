---
name: image-context-bridge
description: auto_image가 추출 이미지를 찾는 일반 메커니즘 — 슬라이드 출처텍스트 index.yaml + 키워드 점수
metadata: 
  node_type: memory
  type: project
  originSessionId: 582367a4-8673-48f1-a75f-d121aba04a1b
---

`auto_image`가 KB의 *추출* 이미지(기계명 pptx_imageN)를 의미적으로 찾는 일반 브리지 (2026-05-26 구현).

**구조**:
1. `extract_images_from_docs.py` — pptx를 슬라이드 단위로 파싱(rels로 이미지↔슬라이드 연결), 각 추출 이미지에 *출처 슬라이드 텍스트*를 `kb/company/{company}/images/extracted/index.yaml`에 기록 (`{file, source, context_text}`).
2. `fill_hwpx_form.py`의 `search_kb_image` 3순위: ① 큐레이트 의미명 파일(`org_chart.png` 등, 사람 배치) → ② **index 키워드 매칭**(fill 컨텍스트가 고른 스키마 키워드가 각 이미지 context_text에 몇 개 나오는지 점수, 동점이면 큰 파일) → ③ 약한 fallback.

**설정**(`kb/image_schema.yaml` search_config, 매직넘버 코드에 안 박음): `index_min_bytes`/`index_max_bytes`(애니gif·초대형 배경 제외), `index_latin_min_len`(짧은 영문키워드 substring 오탐 방지).

**Why**: 임의 회사 KB·임의 양식 동작. 코드에 회사·이미지명 하드코딩 0(grep 검증). 회사별 건 index.yaml *데이터*뿐. [[feedback_generalization]] [[feedback_no_overfit]] 준수.

**한계·How to apply**: deck에 해당 개념의 *실제 도식*이 있으면 잘 찾음(제품→실제 제품 스크린샷 ✅). 없으면 장식 이미지/오탐 → 그땐 큐레이트 1순위 슬롯에 진짜 파일 배치로 override. *제안 특정* 이미지는 generic 컨텍스트로 못 고르므로 `insert_image` 명시 경로 권장. 관련 [[image-insertion-feature]].
