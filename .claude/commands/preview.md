---
description: 빌드된 .pptx 파일의 슬라이드를 즉시 PNG 썸네일로 추출해 Claude가 시각적으로 검토한다. 발표자료가 의도대로 나왔는지 확인용.
---

# /preview 명령

## 사용법

```
/preview <pptx 경로>
/preview <pptx 경로> <슬라이드 번호 또는 범위>
```

예시:
```
/preview output/20260518/발표자료_AI상용화_V1.pptx
/preview output/20260518/발표자료_AI상용화_V1.pptx 1
/preview output/20260518/발표자료_AI상용화_V1.pptx 1-5
/preview output/20260518/발표자료_AI상용화_V1.pptx 20,25,30
```

## 동작

1. **썸네일 렌더링** — `python3 scripts/render_thumbnails.py <pptx>` 호출. 결과는 `<pptx_basename>.thumbnails/slide_NN.png`.

2. **슬라이드 범위 결정**
   - 인자 없음: 전체 슬라이드
   - 단일 번호: 그 한 장만
   - 범위(`1-5`): 1~5번
   - 콤마(`1,5,10`): 명시된 것만

3. **시각 검토** — Claude가 각 PNG를 Read 도구로 읽고:
   - 표지: 사업명·발주처·제안사 표시 + 디자인 자산 보존
   - 목차: 섹션 번호/제목 깔끔
   - 간지: 장번호/장이름 명확
   - 본문: 텍스트·이미지 overflow 없음, 가독성 OK
   - 감사: 메시지 정렬·디자인

4. **이슈 보고** — 슬라이드별 문제점 발견 시:
   - 어느 슬라이드가 문제인지 명시 (`slide N`)
   - 추정 원인 (예: "이미지가 텍스트와 겹침", "폰트가 너무 작음")
   - 가능하면 yaml 어느 키 수정하면 되는지 안내

5. **종합 평가** — 5장 이상 검토 시 종합 점수·우선 수정 사항 정리

## 출력 예시

```
preview 요약 (output/20260518/발표자료_AI상용화_V1.pptx, 31장):

✓ slide 1 (표지): 사업명·발주처·일자 정상. AI 그래픽 보존
✓ slide 2 (목차): 섹션 6개 깔끔
⚠ slide 20 (본문): 우측 텍스트가 디자인 막대에 가림 → style.yaml의 remove_decorative_pictures 확인
✓ slide 30 (사업비): bar_chart 자동 변환 OK
...

종합: 5/35 슬라이드에서 미세 이슈. 수정 권장 우선순위: ...
```

## 주의

- 썸네일 렌더링에 LibreOffice 필요 (.pptx → PDF → PNG)
- 시간 소요: 슬라이드 30장 기준 약 1~2분
- 한 번 렌더된 썸네일은 `.thumbnails/` 폴더에 캐시 — pptx 수정 후 재실행 시 갱신
- 빠른 확인이 목적이면 일부 슬라이드만 (`1-5` 또는 콤마 구분) 검토

## 관련

- `/rfp` — RFP → PPT 전체 흐름
- `/proposal` — 제안서 → PPT
- `/verify-template` — 템플릿 매핑 검증 (다른 용도)
