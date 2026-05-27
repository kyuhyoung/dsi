# 일반화 원칙 — 하드코딩/오버피팅 금지

> 2026-05-26 사용자 피드백

## 핵심 원칙

**임의의 회사, 임의의 RFP, 임의의 양식에 대해서도 동작해야 한다.**

- 특정 양식(농식품AI 등)에 하드코딩 금지
- 특정 예제에 오버피팅 금지
- 모든 로직은 일반화된 규칙 기반이어야 함

### 데이터 ≠ 하드코딩 (중요 구분)

하드코딩 금지는 *코드·로직*에 적용된다. *KB 데이터*가 회사별인 건 정상 — KB의 존재 이유다.
- OK: `kb/company/dabeeo/intro.md`에 다비오 사업자등록번호(105-87-68437) 저장. lig면 `kb/company/lig/`에 그 회사 값. (회사별 KB 데이터)
- 금지: 코드에 `if company=="dabeeo"`, 값 박기, 특정 field명→특정 경로 lookup 테이블, 특정 양식만 트리거되는 분기.
- field→KB 매칭은 *코드 lookup 테이블*이 아니라 proposal-writer(LLM)가 양식 라벨+회사 KB를 읽어 수행 → 임의 회사·양식 동작. fill_hwpx_form 은 fills.yaml 입력만 받고 KB 매칭을 코드로 하지 않음.
- 검증법: `grep -riE 'dabeeo|농식품|특정값' scripts/` 가 로직에서 0건이어야 (docstring 예시는 무해).

## 현재 문제점

### 1. fills.yaml 수동 작성
- `fills_본체별지3_v4.yaml`이 농식품AI 양식에 특화되어 수동 작성됨
- 새 양식이 오면 처음부터 다시 작성해야 함

### 2. 필드 → KB 매칭 수동
- "대표자" 필드를 보고 KB에서 가져와야 한다는 판단을 사람이 함
- `(확인 필요)` 같은 플레이스홀더를 수동으로 채움

### 3. 레이아웃 셀 판단 수동
- T16_R2_C0이 입력란인지 레이아웃용 빈 셀인지 사람이 판단
- 잘못 판단하면 입력란이 아닌 곳에 텍스트 삽입

## 개선 방향

### 1. 필드 → KB 자동 매칭

form.yaml의 셀 정보를 보고 KB에서 자동 검색:

```yaml
# form.yaml 셀 예시
- id: T14_R2_C1
  text: '홍 길 동'
  hints:
    left: '대 표 자'  # ← 이 라벨을 보고 KB 검색
```

매칭 로직:
1. `hints.left` (왼쪽 라벨) 정규화: "대 표 자" → "대표자"
2. KB 스키마에서 매칭: "대표자" → `kb/company/{company}/intro.md#대표이사`
3. 값 추출: "박주흠"

### 2. KB 스키마 정의

```yaml
# kb/schema.yaml (신규)
field_mappings:
  대표자: 'company/*/intro.md#대표이사'
  대표이사: 'company/*/intro.md#대표이사'
  회사명: 'company/*/intro.md#정식 회사명'
  설립일: 'company/*/history.md#설립'
  설립: 'company/*/history.md#설립'
  사업자등록번호: 'company/*/registration.md#사업자등록번호'
  법인등록번호: 'company/*/registration.md#법인등록번호'
  업종: 'company/*/intro.md#업종'
  # ... 추가 매핑
```

### 3. 레이아웃 셀 자동 인식

`empty_input` intent지만 입력란이 아닌 경우 자동 판단:

```python
def is_layout_cell(cell, table):
    """레이아웃용 빈 셀인지 판단."""
    # 1. hints가 전혀 없으면 레이아웃 셀 가능성 높음
    if not cell.get('hints'):
        return True

    # 2. 같은 행의 다른 셀이 subordinate(↳)로 시작하면,
    #    이 셀은 들여쓰기를 위한 빈 공간
    row_cells = [c for c in table['cells'] if c['row'] == cell['row']]
    for rc in row_cells:
        if rc.get('intent') == 'subordinate':
            return True

    # 3. 위/아래 셀이 라벨이고 이 셀만 빈칸이면 레이아웃
    # ...

    return False
```

### 4. proposal-writer 에이전트 역할

form.yaml 입력 → fills.yaml 자동 생성:

1. form.yaml의 모든 `fill_targets` 셀 순회
2. 각 셀의 `hints.left` (라벨) 추출
3. KB 스키마에서 매칭되는 값 검색
4. 매칭되면 fills에 추가, 안 되면 `(KB 미확인)` 표시
5. 레이아웃 셀은 자동 skip

## 구현 우선순위

1. **KB 스키마 정의** — 필드명 ↔ KB 경로 매핑
2. **라벨 정규화 함수** — "대 표 자" → "대표자"
3. **KB 자동 검색 함수** — 스키마 기반 값 추출
4. **레이아웃 셀 판단 함수** — intent + 맥락 기반
5. **proposal-writer 에이전트 개선** — 위 함수들 활용하여 fills.yaml 자동 생성

## 검증 기준

- 새 양식(F16PBU, 민군 등)에 코드 수정 없이 동작
- 새 회사 KB 추가 시 코드 수정 없이 동작
- fills.yaml 수동 작성 0건 목표

## 이미지 삽입 일반화 (2026-05-26 추가)

### 원칙

- **KB 기존 이미지 우선** — 생성보다 가져오기
- `kb/image_schema.yaml`로 키워드 → 경로 매핑
- `{company}` 플레이스홀더로 회사별 이미지 폴더 지원

### fills.yaml 스키마

```yaml
# 방법 1: 명시적 경로
- id: T18_R3_C3
  operation: insert_image
  image_path: kb/company/dabeeo/images/product.png

# 방법 2: KB 자동 검색 (권장)
- id: T18_R3_C3
  operation: auto_image
  context: '제품 이미지'  # 또는 hints: {left: '조직도'}
```

### KB 이미지 폴더

```
kb/company/{company}/images/
  product_main.png    # 제품 대표
  org_chart.png       # 조직도
  architecture.png    # 시스템 구성도
  ...
```

상세: `memory/image_insertion_feature.md`
