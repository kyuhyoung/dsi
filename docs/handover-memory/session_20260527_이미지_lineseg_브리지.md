# 세션 인수인계 — 2026-05-27 이미지 삽입·linesegarray·context 브리지

직전 세션(2026-05-26)에서 시작한 *이미지 삽입* 작업을 이어, 검증·근본수정·일반 브리지·셀 자기검증 규칙까지 완료한 스냅샷.

## 이 세션이 한 일 (요약)

| 영역 | 내용 | 상태 |
|---|---|---|
| 이미지 삽입 검증 | v14/v16 한컴 PDF 렌더로 T18_R3_C3 이미지 정상 표시 확인 | ✅ |
| **텍스트 겹침 근본수정** | `set_cell_text`가 stale `<hp:linesegarray>` 미삭제 → 긴 텍스트 한컴 겹침. `set_paragraph_text`와 동일하게 삭제하도록 수정 | ✅ |
| 일반성 실증 | 민군규격표준화 양식(다른 양식)에 코드수정 0으로 채움 → PDF 텍스트추출로 5줄 정확 줄바꿈 확인 | ✅ |
| **추출→스키마 context 브리지** | `extract_images_from_docs.py`가 슬라이드 텍스트↔이미지 연결 → `extracted/index.yaml`. `search_kb_image` 3순위(큐레이트→index 키워드매칭→fallback) | ✅ |
| proposal-writer 셀 자기검증 | 셀 의미↔내용 일치 검증 규칙 추가 (위치 추측 금지). T17 사업비 셀에 회사명 오입력 버그의 일반 예방 | ✅ |
| KB | 다비오 사업자등록번호 105-87-68437 → `kb/company/dabeeo/intro.md` | ✅ |

## 핵심 코드 변경 (이 세션, scripts/)

- `fill_hwpx_form.py`
  - `set_cell_text`: 기존 run 전부 제거 + **linesegarray 삭제**(한컴 줄바꿈 재계산) + 녹색 off 시 원본 charPr 유지
  - `search_kb_image`: 3순위 검색 + `_search_index_image`(index.yaml 키워드 점수, 크기/짧은영문키워드 bound는 `image_schema.yaml`)
  - 이미지 삽입(`insert_image`/`auto_image`): hp:pic + BinData + content.hpf 등록
  - `company` 기본값 "dabeeo"→None(전체 탐색)
- `extract_images_from_docs.py`: pptx 슬라이드 단위 파싱(rels로 이미지↔슬라이드) → 추출 이미지에 context_text 기록 → `index.yaml`
- 신규 검증 유틸: `hwpx_to_pdf.py`(SetMessageBoxMode 필수!), `pdf_to_png.py`, `render_page_region.py`, `crop_png.py`, `find_image_pages.py`
- `kb/image_schema.yaml`(신규): 키워드↔의미명 매핑 + search_config(크기·키워드 bound)
- `.claude/agents/proposal-writer.md`: 셀 의미↔내용 자기검증 규칙

## 남은 갭 (다음 세션)

1. **녹색 글자 opt-in** — 채운 텍스트 강제 녹색(#00AA00)이 무조건 적용 중. 제출물엔 검은 글자 필요. `add_green_char_style` 호출을 `--mark-fills` 플래그로(기본 off). [[green-text-must-be-optin]]
2. **T17 사업비 구성 재작성** — `output/20260524/fills_본체별지3_v4.yaml`의 T17이 회사명 오입력 + 자기부담금/국고 금액칸 공백. proposal-writer 재실행(새 자기검증 규칙 적용)으로 재작성 필요. *예산 수치는 손으로 박지 말 것*(overfit).
3. **이미지 브리지 실데이터** — `extracted/`(312MB)는 미커밋(거대). 소스 deck도 미커밋. clone 후 `extract_images_from_docs.py`를 회사 deck에 재실행해야 index.yaml·이미지 생성됨.

## 산출물 위치 (이 세션, output/20260526/)

- `농식품AI_filled_v16.hwpx/.pdf` — 통합양식 전체 채움 (47p, 최신)
- `본체_v16/01_[별지_제3호]_사업계획서.hwp/.pdf` — **본체 사업계획서 1개**(별지 제3호, 계속 체크하던 산출물)
- `민군_filled_test.*` — 일반성 실증 (다른 양식)
- 분할 sections yaml: `output/20260524/통합양식_v3.form.yaml` (별지 7개 자동 검출)

## 일반화 원칙 (사용자 반복 강조)

코드에 회사·양식·example 하드코딩 절대 금지. KB 데이터(회사별)는 OK, *로직*은 일반. 검증: `grep -riE 'dabeeo|농식품' scripts/`가 로직에서 0건. 새 양식엔 *반드시 2번째 양식에 돌려 실증*. [[feedback_generalization]] [[feedback_no_overfit]]
