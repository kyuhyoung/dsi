---
description: 새/변경된 PPT template을 자동 발견·분석·등록한다. 인자 없으면 templates/ 폴더 전체 스캔. 새 회사 template 추가 후 한 줄로 onboarding 완료.
---

# /onboard-template 명령

## 사용법

```
/onboard-template                # 자동 발견 모드 (권장)
/onboard-template <name>         # 특정 template만 처리
/onboard-template --force        # 모든 template 재처리 (style.yaml 무시)
```

예시:
```
cp ~/Downloads/SDS_template.pptx templates/
/onboard-template
```

## 자동 발견 모드 (인자 없음)

### 1. templates/ 스캔

`templates/*.pptx` 모두 발견. 각각에 대해 처리 대상 여부 판단:

| `.pptx` 상태 | `.style.yaml` 상태 | 액션 |
|---|---|---|
| 존재 | 없음 (신규) | **처리** |
| 존재 | `.pptx` 보다 오래됨 | **처리** (template 수정됨) |
| 존재 | `.pptx`와 동등 또는 최신 | 스킵 |
| 없음 | 있음 | 경고 (orphan) |

처리 대상 발견 시 *원시 데이터 추출 + LLM 분석* 흐름 (아래 동작 흐름 참조).

### 2. 처리 대상 0개

```
모든 template 최신. onboarding 불필요.
사용 가능 template: <목록>
```

종료.

### 3. 처리 대상 N개

각각 순차 처리:
- `template-analyzer` subagent 자동 호출
- 약한 매핑 vision 보강
- 사용자 검토 요청

여러 template이면 1개씩 처리하고 사용자 승인 후 다음.

## 명시 모드 (`/onboard-template <name>`)

`templates/<name>.pptx` 단 1개만 처리. `.style.yaml` 존재 여부 무관.

## --force 모드

`templates/*.pptx` 모두 *재처리*. 기존 `.style.yaml` 백업 후 재생성. 자동 분석 알고리즘 업그레이드 후 일괄 갱신용.

## 동작 흐름

```
1. 처리 대상 결정
   → templates/*.pptx 스캔, .style.yaml 없거나 .pptx보다 오래된 것 식별

2. 각 처리 대상에 대해:
   2-a. 원시 데이터 추출 (PY)
        python3 scripts/analyze_template.py <template.pptx> --raw <template>.raw.yaml
        → layouts·slides·shapes·theme *원시 dump*. 의미 분석 0.

   2-b. 썸네일 렌더
        python3 scripts/render_thumbnails.py <template.pptx>
        → templates/<name>.thumbnails/slide_NN.png 생성

   2-c. *template-analyzer subagent 호출* (LLM, vision)
        subagent가 직접:
        - raw.yaml의 layouts·slides 정보 + 썸네일 본다
        - layout 이름·디자인에서 *챕터 구조* 의미 추출
        - 슬라이드 종류 (표지/목차/간지/회사소개/본문/감사) 의미 분류
        - 본문 견본을 *챕터별*로 그룹화 (body_samples_by_chapter)
        - slot 위치, dummy_texts, 색·폰트 결정
        - style.yaml 작성

3. 사용자 검토
   - 각 template의 최종 매핑 요약 출력
   - "이상 없음" / "수정" / "다음으로"
```

**핵심 변경 (2026-05-20)**: PY 자동 매핑·점수·휴리스틱 *폐지*. 모든 의미 판단은 LLM (template-analyzer agent).
- 이유: 회사·언어·디자인 시스템마다 명명·구조 다름. PY 정규식·키워드는 일반화 안 됨.
- 효과: 어떤 template (한국어/영문/일문, `01. ~`/`Part I`/`第三章` 등)도 LLM이 vision으로 직접 처리.

## 사용자 검토 옵션

각 template 처리 후 다음 응답 대기:
- `진행` `ok` — 매핑 승인, 다음 template로
- `수정: <설명>` — Claude가 yaml 추가 조정
- `재분석` — template-analyzer 다시 호출
- `보류` — 이 template 스킵, 다음으로

## 출력 형식

```
[발견] 새/변경 template <N>개:
  1. templates/A.pptx
  2. templates/B.pptx

[1/N] A 처리 중...
  → analyze_template.py: 표지/간지/회사소개 자동, 본문 약함
  → 썸네일 41장 렌더
  → vision 보강: 본문 변종 식별 (기본=10, 이미지=15, 표=30)
  → dummy_texts 추가 32개

  매핑 요약:
    표지: 1     간지: 2     회사소개: 3
    본문: {기본:10, 이미지:15, 표:30}
    감사: 41
  ▸ 검토하시겠습니까?

(승인 후)
[2/N] B 처리 중...
   ...

모든 template onboarding 완료.
이제 /proposal·/rfp 빌드 시 새 template 자동 사용.
```

## 관련

- `/proposal` — 제안서 → PPT (빌드 시 자동으로 template style.yaml 점검)
- `/rfp` — RFP → PPT (동일)
- `/preview` — 빌드 결과 시각 검토
- `/verify-template` — 기존 template 매핑 비전 검증 (수동)

## 주의

- 회사 template이 *발표 자료* (콘텐츠 + 디자인 융합) 인 경우 vision 보강이 필수. 분석기 단독으로는 부족.
- *깔끔 정리본* (회사 디자인만, 발표 콘텐츠 비움) 권장 — vision 보강 불필요할 수도.
- 한 번 onboarding 후 `<name>.style.yaml` 캐시. 이후 빌드는 즉시.
- template 수정 시 `.pptx` mtime이 갱신되어 자동 재처리.
