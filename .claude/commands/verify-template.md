---
description: 템플릿 .pptx의 자동 매핑(.style.yaml)을 슬라이드 썸네일로 비전 검증한다. 잘못된 매핑이 있으면 수정 제안.
---

# /verify-template 명령

## 사용법

```
/verify-template <템플릿이름>
```

예시:
```
/verify-template Dabeeo_PPT_Template_V1
/verify-template AcmeCorp_Master
```

`<템플릿이름>`은 `templates/<name>.pptx` 의 파일명에서 `.pptx`를 뺀 부분입니다.

## 동작

1. **썸네일 확인** — `templates/<name>.thumbnails/slide_NN.png` 가 있는지 확인. 없으면 `python3 scripts/render_thumbnails.py templates/<name>.pptx` 실행해서 생성.

2. **현재 매핑 로드** — `templates/<name>.style.yaml` 의 `template.layouts` 섹션 읽기. 각 종류(표지·목차·간지·회사소개·본문·감사)가 어느 슬라이드 번호로 매핑됐는지 확인. 변종 dict인 경우 모든 변종 확인.

3. **약한 매핑 식별** — `_auto_mapping_scores` 섹션에서 점수가 5 미만이거나 null인 종류를 우선 검토 대상으로 추림.

4. **비전 검증** — 각 약한 매핑에 대해:
   - 매핑된 슬라이드 썸네일(`slide_NN.png`)을 Read 도구로 읽음
   - 시각적으로 그 종류에 맞는지 판단
   - 안 맞으면 다른 슬라이드 썸네일들도 훑어서 진짜 후보 찾기

5. **수정 제안** — 매핑 변경이 필요하면 사용자에게 *어떤 종류를 몇 번으로 바꾸겠다*고 제안하고 승인 받은 후 style.yaml의 `template.layouts` 수정.

6. **재빌드 권장** — 매핑 변경 시 영향받는 산출물이 있으면 재빌드 안내.

## 검증 체크리스트

각 종류별로 다음을 확인:

| 종류 | 시각적 특징 |
|---|---|
| 표지 | 큰 제목 + 부제 + 회사 로고. 슬라이드 1~3 근방 |
| 목차 | "목차"/"Contents"/"Agenda" 텍스트 + 번호 매겨진 항목 |
| 간지 | 큰 챕터 번호 + 챕터명. 본문 사이 구분 페이지 |
| 회사소개 | "회사", "Company", "About us" 같은 제목 |
| 본문 | 제목 + 본문 영역. 변종(이미지·표·차트·이단) 별로 확인 |
| 감사 | "감사합니다"/"Thank you" 중앙 정렬 |

## 안 맞을 때

- 점수가 0이면 그 종류 슬라이드가 템플릿에 없을 가능성 → null로 두고 코드 fallback 사용
- 점수는 낮은데 적합한 슬라이드가 있으면 → style.yaml 수동 수정
- 변종(본문 dict)이 잘못 분류됐으면 → `template.layouts.본문` dict 수정 또는 단일 int로 단순화

## 주의

- 슬라이드 번호는 1-based (사람 친화)
- 회사 디자인 의도와 다른 매핑은 *추측 말고* 사용자에게 확인 받기
