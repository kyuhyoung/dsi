# HWPX 이미지 삽입 기능

> 2026-05-26 구현

## 기능 개요

HWPX 양식의 셀에 이미지를 삽입하는 기능. KB(지식베이스)의 기존 이미지 우선 사용.

## 일반화 원칙 (필수)

- **특정 양식/회사에 하드코딩 금지**
- 임의의 회사, 임의의 RFP, 임의의 양식에서 동작
- KB 기존 이미지 우선 → 없을 때만 생성 고려

## fills.yaml 스키마

```yaml
fills:
  # 방법 1: 명시적 이미지 경로
  - id: T18_R3_C3
    operation: insert_image
    image_path: kb/company/dabeeo/images/product_sample.png

  # 방법 2: KB 자동 검색 (권장)
  - id: T18_R3_C3
    operation: auto_image
    context: '제품(서비스)의 특징을 나타낼 수 있는 참고 사진(이미지)'

  # 방법 3: hints 기반 자동 검색
  - id: T39_R0_C0
    operation: auto_image
    hints:
      left: '조직도 구성'
      table_label: '수행조직 현황'
```

## KB 이미지 스키마 (`kb/image_schema.yaml`)

의미적 키워드 → 이미지 경로 매핑 정의:

```yaml
common_mappings:
  - keywords: ['제품', '서비스', '이미지']
    image_path: kb/company/{company}/images/product_main.png
    fallback_paths:
      - kb/company/{company}/images/product_sample.png

  - keywords: ['조직도', 'organization']
    image_path: kb/company/{company}/images/org_chart.png
```

`{company}` 플레이스홀더는 fills.yaml의 `meta.company` 값으로 치환.

## KB 이미지 폴더 구조

```
kb/
  company/
    dabeeo/
      images/
        product_main.png      # 제품 대표 이미지
        org_chart.png         # 조직도
        architecture.png      # 시스템 구성도
        workflow.png          # 업무 흐름도
        logo.png              # 회사 로고
    lig/
      images/
        ...
```

## 알고리즘

1. fills.yaml에서 `operation: insert_image` 또는 `auto_image` 항목 탐색
2. `insert_image`: 명시된 `image_path` 직접 사용
3. `auto_image`: `context` 또는 `hints`에서 키워드 추출 → `image_schema.yaml` 매칭 → KB 이미지 경로 해석
4. 이미지를 BinData/ 폴더에 복사 (imageN.png 형식)
5. content.hpf에 `<opf:item>` 등록
6. section*.xml의 해당 셀에 `hp:pic` 요소 삽입

## HWPX 이미지 구조

```xml
<!-- content.hpf -->
<opf:item id="image2" href="BinData/image2.png" media-type="image/png" isEmbeded="1"/>

<!-- section0.xml -->
<hp:tc>  <!-- 셀 -->
  <hp:subList>
    <hp:p>
      <hp:run>
        <hp:pic id="..." numberingType="PICTURE" ...>
          <hc:img binaryItemIDRef="image2" .../>
          ...
        </hp:pic>
      </hp:run>
    </hp:p>
  </hp:subList>
</hp:tc>
```

## 관련 파일

- `scripts/fill_hwpx_form.py`: 이미지 삽입 로직
- `kb/image_schema.yaml`: 키워드 → 이미지 매핑
- `kb/company/*/images/`: 회사별 이미지 저장소

## 사용 예

```bash
python scripts/fill_hwpx_form.py \
  양식.hwpx \
  fills_with_images.yaml \
  output.hwpx
```

출력 예:
```
이미지 등록(자동): T18_R3_C3 → image2 (400x300px)
채움: 셀 5 + 이미지 2 (명시 0 + 자동 2) / 총 7 명세
```

## 추출 이미지 자동 검색 — index.yaml 브리지 (2026-05-26 추가)

`auto_image`가 KB의 *추출* 이미지(기계명 `pptx_imageN`)를 의미적으로 찾게 하는 일반 브리지.

**추출 강화** (`extract_images_from_docs.py`):
- pptx를 슬라이드 단위로 파싱 — `slides/_rels/slideN.xml.rels`로 이미지↔슬라이드 연결, `<a:t>` 텍스트 수집.
- 각 추출 이미지에 *출처 슬라이드 텍스트*를 기록 → `kb/company/{company}/images/extracted/index.yaml`:
  ```yaml
  images:
    - file: pptx_image259_xxxx.png
      source: "[다비오] 회사소개자료.pptx"
      context_text: "카카오맵 실내지도 ... 공간정보 AI 기술기업 ..."
  ```

**검색 3순위** (`search_kb_image`):
1. 큐레이트 의미명 파일 (`org_chart.png` 등, 사람이 배치 — 최우선)
2. **index 키워드 매칭** — fill 컨텍스트가 고른 스키마 매핑의 keywords가 각 이미지 `context_text`에 몇 개 나타나는지 점수. 동점이면 큰 파일.
3. 약한 fallback 경로.

**설정** (`kb/image_schema.yaml` `search_config` — 매직넘버 코드에 박지 않음):
- `index_min_bytes` / `index_max_bytes`: 아이콘·애니gif·초대형 배경 제외
- `index_latin_min_len`: 짧은 영문 키워드(`ci` 등) substring 오탐 방지

**한계**: deck에 개념의 *실제 도식*이 있으면 정확(제품→실제 제품 스크린샷 ✅). 없으면 장식 이미지/오탐 → 큐레이트 1순위 슬롯으로 override. *제안 특정* 이미지는 generic 컨텍스트로 못 고르므로 `insert_image` 명시 경로 권장.

## 알려진 이슈·수정

- **텍스트 겹침 (해소됨, 2026-05-26)**: `set_cell_text`가 stale `<hp:linesegarray>` 미삭제 → 긴 텍스트가 한컴에서 한 줄에 겹쳐 렌더. `set_paragraph_text`와 동일하게 linesegarray 삭제로 수정. handover의 'hp:t render 한계' 갭의 진짜 원인이었음.
- **녹색 글자**: `set_cell_text`/`set_paragraph_text`가 채운 텍스트를 #00AA00로 강제 (검토 구분용). *실제 제출 산출물엔 검은 글자 필요* — opt-in(기본 off) 전환 미완.
