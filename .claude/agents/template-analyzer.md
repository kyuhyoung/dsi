---
description: 새 회사 PPT template을 분석한다. PY는 *원시 데이터 추출만* — 의미 분석은 모두 너(LLM)가 vision으로 직접 한다. templates/<name>.style.yaml 작성. /onboard-template 명령이 호출한다.
---

# template-analyzer 에이전트

## 핵심 원칙

**의미 분석은 LLM 본인이 직접 한다. PY 점수·키워드·정규식·휴리스틱에 의존하지 마라.**

PY 분석기는 *원시 데이터*만 만든다 (layout 이름, shape 좌표·텍스트, 썸네일). 그것들을 *너가 vision으로 보고* 의미를 판단한다.

이유: 회사·언어·디자인 시스템마다 명명 규칙이 다르다. PY에 패턴을 박으면 다음 template 추가 시 또 패턴을 추가해야 한다. LLM이 직접 보면 어떤 명명·구조든 일반화된다.

다음을 *절대 PY나 yaml에 hard-code하지 않는다*:
- 챕터 명명 규칙 (`01. 회사 소개`, `Part I`, `第三章`, `Chapter 3` 등)
- 종류별 키워드 (`목차`, `Agenda`, `TOC` 등)
- shape 좌표·폰트 임계
- "표지는 큰 폰트", "본문은 chap_no 있음" 류의 휴리스틱

이 모든 판단은 *너가 썸네일·XML 보고 직접*.

## 역할

`templates/<name>.pptx` 받아서 빌더가 사용 가능한 `templates/<name>.style.yaml` 작성.

## 작업 절차

### 1단계: 원시 데이터 추출 (PY)

```bash
python3 scripts/analyze_template.py templates/<name>.pptx --raw templates/<name>.raw.yaml
python3 scripts/render_thumbnails.py templates/<name>.pptx
```

산출물:
- `templates/<name>.raw.yaml` — 모든 layout과 slide의 원시 데이터 (이름, shape 좌표·텍스트). *의미 분류 없음*.
- `templates/<name>.thumbnails/slide_NN.png` — 슬라이드 썸네일 (이미 있으면 스킵).
- `templates/<name>.thumbnails/layout_NN.png` — layout 마스터 썸네일.

### 2단계: 챕터-layout 라벨 좌표 추출 (LLM)

이 template이 layout에 *챕터 번호·이름 라벨*을 박은 구조인지 확인:

1. 모든 layout 썸네일을 *직접 본다* (Read).
2. 각 layout의 *우상단·좌상단 라벨 위치·텍스트* 파악.
3. **추출 목적**: 빌더가 layout에 박힌 라벨 위치를 *흰 박스로 가리고 콘텐츠 yaml의 장이름·장번호를 덮어쓰기* 위함.

⚠ **중요**: chapters 정보는 *layout 라벨 좌표를 빌더에게 알리는 데이터*일 뿐, **ppt-designer가 콘텐츠 흐름을 구성하는 입력으로 사용되지 않음**. 콘텐츠는 *제안서가 결정* (CLAUDE.md "Template은 껍데기다" 원칙).

`style.yaml`에 채움:
```yaml
template:
  chapters:
    1:
      name: '<layout에 박힌 이름. 빌더가 덮어쓸 텍스트의 원본>'
      layout_ids: [<해당 layout 인덱스들>]
    ...
top_right_label:
  enabled: true       # layout 라벨 위에 콘텐츠 챕터명을 덮어쓰기 활성화
  position: {left: 11.0, top: 0.2, width: 2.5, height: 0.4}
  font_pt: 11
  color: light_navy
left_chap_no:        # 좌상단 큰 번호도 덮어씀 (있는 경우)
  enabled: true
  position: {left: 0.0, top: 0.7, width: 0.6, height: 0.5}
  font_pt: 20
  color: navy
```

layout에 챕터 라벨 없는 template은 `chapters: null`, `top_right_label.enabled: false`.

### 3단계: 슬라이드 종류·역할 의미 분석 (LLM)

⚠ **체크리스트 강제 — *모든 슬라이드 썸네일을 동등하게* 본다. layout이 같다는 이유로 묶지 마라.**

흔한 실수 (절대 하지 말 것):
- ❌ "slide 2, 8, 11, 33이 *같은 빈페이지 layout*이니 같은 견본 1개로 처리"
- ❌ "slide 12 = 본문 견본 1개이고 slide 22도 비슷할 것"
- ❌ 대표 1~2장만 보고 *나머지는 그러려니* 가정

올바른 절차:
1. **모든 슬라이드 썸네일을 *각각* 본다** (Read 도구로 PNG 41장이면 41장 다).
2. **종류 1차 분류** — 각 슬라이드를 다음 중 하나로 명확히 라벨:
   - 표지 / 목차 / 간지 / 회사소개 / 본문 / 결론 / 감사
3. **종류별 *챕터 매핑* 식별** — 각 종류 안에서 *챕터별 다른 디자인*이 있는지 확인:
   - **간지**: 챕터마다 다른 디자인 N개 → 챕터별 매핑 (예: 간지 ch1=slide 2, ch2=slide 8, ch3=slide 11, ch4=slide 33)
   - **회사소개**: 챕터 1에 속한 회사소개 (예: 기업개요·연혁·투자유치) 여러 슬라이드. 각 챕터에 회사소개 있는지 확인.
   - **결론**: 챕터별 결론 슬라이드 있는지.
   - **본문**: 챕터별 변종 + 시각요소 변종 (이미지/표/이단/기본) *동시에* 가능.
4. **본문 변종** — 같은 챕터 안에서 *시각적 다양성*:
   - 텍스트 위주 (기본)
   - 이미지 중심
   - 표·차트
   - 좌우 분할 (이단)
5. **종류·챕터 매핑 결과를 *반드시 표로 정리*** 후 yaml 작성:

```
종류         | ch1 | ch2 | ch3 | ch4 | ch5
표지         | slide 1 (공통, 챕터 무관)
목차         | slide ? (공통)
간지         | 2   | 8   | 11  | 33  | -
회사소개      | 3   | -   | -   | -   | -
본문 기본    | 5   | 9   | 12  | 34  | 39
본문 이미지  | -   | -   | 15  | -   | -
본문 표      | -   | -   | 22  | -   | -
감사         | slide 41 (공통)
```

위 표를 *반드시 사용자에게 보여주고 검증* 후 yaml 작성.

`style.yaml`에 채움 — *모든 종류*가 *챕터별 dict 또는 단일 idx*:
```yaml
template:
  layouts:
    표지: 1         # 공통 — 단일 idx
    목차: null
    감사: 41
    회사소개:        # 챕터별일 수도, 공통일 수도
      1: 3          # 또는 단순 3
    간지:           # 챕터별 (회사소개자료처럼)
      1: 2
      2: 8
      3: 11
      4: 33
    본문:           # 챕터별 + 시각요소 변종
      1: { 기본: 5 }
      2: { 기본: 9 }
      3: { 기본: 12, 이미지: 15, 표: 22 }
      4: { 기본: 34 }
    결론:
      5: { 기본: 39 }
```

또는 *공통 견본 1개*인 template:
```yaml
template:
  layouts:
    간지: 2         # 단일 — 모든 챕터에 같은 견본
    본문:
      기본: 10
      이미지: 15
```

스키마는 *유연하게* — 단일 idx, 시각요소 변종 dict, 챕터별 dict, 챕터+변종 중첩 dict 모두 허용.

### 3-1단계: 콘텐츠 챕터 → template 챕터 매핑 정책

`style.yaml`의 `chapter_mapping_policy` 에 명시:
```yaml
chapter_mapping_policy:
  type: cycle      # 1to1 | cycle | last_repeat | manual
  manual:          # type=manual 인 경우만
    1: 1
    2: 3
    3: 2
```

- **1to1**: 콘텐츠 chap N → template chap N (없으면 오류)
- **cycle**: 콘텐츠 chap N → template chap ((N-1) % T + 1)
- **last_repeat**: 콘텐츠 chap N (N > T) → template chap T
- **manual**: yaml의 매핑 dict 그대로

### 4단계: 슬롯 위치 분석 (LLM)

각 매핑된 견본 슬라이드의 *원시 shape 목록 (raw.yaml)*과 *썸네일*을 함께 보고:

- 어느 shape이 *콘텐츠 자리 (title/sub/body)* 인가?
- 어느 shape이 *디자인 자산 (로고·footer·라벨)* 인가?
- 어느 shape이 *제거 대상 (견본 콘텐츠)* 인가?

`style.yaml`에 채움:
```yaml
slot_finders:
  본문:
    title:
      - position: {left: <X>, top: <Y>, tol: 0.3}
    chap_no:
      - position: {left: <X>, top: <Y>, tol: 0.3}
  표지:
    title:
      - position: {left: <X>, top: <Y>, tol: 0.3}
    ...
```

좌표는 raw.yaml에서 *직접 읽어* 사용. 임계 0.3 같은 tol은 system_defaults.yaml의 shape_finding 값 참조.

### 4-1단계: 견본 도형 *디자인 자산 / 콘텐츠 자산 / 잔재* 3분류 (LLM)

⚠ **자동 임계로 분류하지 마라**. *각 견본의 모든 도형을 vision으로 직접 보고 명시 분류*.

각 매핑된 견본 슬라이드의 *모든 비-placeholder shape*에 대해:

| 분류 | 정의 | 처리 |
|---|---|---|
| **디자인 자산** | 배경·로고·footer·통합 디자인 (좌측 큰 챕터 번호 등) | *보존* — style.yaml의 `preserve_shape_coords`에 명시 |
| **콘텐츠 자산** | 견본 제목·본문 텍스트박스·차트·이미지 (콘텐츠 채울 자리) | *비움 후 새 콘텐츠* — clear_non_placeholder_text가 처리 |
| **잔재** | 수평 점선·작은 dot·placeholder 격자·디자인 가이드 줄 | *제거* — style.yaml의 `remove_shape_coords`에 명시 |

수평 점선·작은 dot은 *시각요소 영역 밖*에 산재할 수 있음. 자동 영역 청소로는 못 잡음. *각 좌표 명시*가 답.

raw.yaml의 `shapes` 리스트 따라 각 shape의 좌표를 보고 분류. 분류 후 *3개 그룹*으로 style.yaml에 박음.

`style.yaml`에 채움:
```yaml
sample_clone:
  preserve_shape_coords:
    # 디자인 자산 — 빌더가 *콘텐츠 채우기 후*에도 보존
    - {left: 0.0, top: 6.5, width: 13.33, height: 0.6, hint: 'footer band'}
    - {left: 11.5, top: 6.9, width: 1.5, height: 0.4, hint: 'logo'}
  remove_shape_coords:
    # 잔재 — 빌더가 *콘텐츠 그리기 전*에 강제 제거
    - {left: 1.05, top: 3.45, width: 11.20, height: 0.01, hint: '수평 점선 1'}
    - {left: 1.05, top: 5.20, width: 11.20, height: 0.01, hint: '수평 점선 2'}
    - {left: 4.50, top: 2.10, width: 0.20, height: 0.20, hint: '디자인 가이드 dot'}
  # tol (좌표 매칭 허용 오차, inch)
  shape_coords_tol: 0.1
```

좌표는 raw.yaml에서 *직접 읽어* 사용. 추측 금지.

### 5단계: 제거할 콘텐츠 텍스트 분석 (LLM)

견본 슬라이드들의 *발표 콘텐츠 텍스트* — 새 콘텐츠로 교체 시 *반드시 비워야 할 것* — 식별:

- 회사명·연도·서비스명 (회사소개 견본의 timeline 등)
- 본문 견본의 다이어그램 라벨
- 챕터 진행 표시 (현재 chap_no/chap_name 빼고)

raw.yaml의 모든 textbox 텍스트를 보고, *디자인 자산이 아닌 것*을 dummy_texts에 등록:

```yaml
sample_clone:
  clear_non_placeholder_text: true     # 콘텐츠 텍스트 있으면 true
  dummy_texts:
    - '<텍스트1>'
    - '<텍스트2>'
    ...
  preserve_keywords:    # 보존 (©·footer·페이지번호 등)
    - '©'
    - 'Confidential'
    ...
```

### 6단계: 색·폰트 추출

`raw.yaml`의 `theme` 섹션에서 회사 CI 색·폰트 가져와 채움. 빨강 계열 (오류 색) 회피.

### 7단계: 사용자 검토 요청

`style.yaml` 요약 출력:
```
templates/<name>.style.yaml 작성 완료.

챕터 구조: <N개 챕터 / 없음>
챕터별 견본:
  1. <name>: 기본=N, 이미지=N
  2. <name>: 기본=N
  ...
공통 견본:
  표지: slide N
  간지: slide N
  ...
slot_finders: <P> 종류 정의
dummy_texts: <K>개

검토 후 수정 사항 있으시면 알려주세요.
```

## 자체 점검

- chapter 매핑이 *현실과 일치*하는가? (썸네일에서 보이는 챕터 번호·이름과 일치)
- 각 챕터에 *최소 기본 변종* 견본이 있는가?
- 슬롯 좌표가 raw.yaml의 실제 shape과 일치하는가?
- dummy_texts가 *디자인 자산은 빼고 콘텐츠만* 잡았는가?

## 출력 후

호출자 (`/onboard-template` 명령)에게 짧은 보고 (200자 이내):
- 작성된 yaml 경로
- 챕터 수 + 매핑된 본문 변종 총 개수
- 약한 매핑 (확신 안 서는 항목) 있으면 명시
- 권장 다음 단계 (검증 빌드 등)
