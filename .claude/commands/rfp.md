---
description: RFP 파일 경로를 받아 분석 → 제안서(.docx) → 발표자료(.pptx)까지 자동 생성한다.
---

# /rfp 명령

## 사용법

```
/rfp <RFP 파일 경로>
```

## 동작 흐름

1. `rfp-analyst` 에이전트로 RFP 파일 분석
2. 분석 결과를 사용자에게 보여주고 확인 받기
3. `proposal-writer` 에이전트로 제안서 본문 작성
4. `scripts/generate_docx.py` 호출 → `.docx` 생성
5. `ppt-designer` 에이전트로 슬라이드 구성
6. `scripts/generate_pptx.py` 호출 → `.pptx` 생성
7. 결과 파일 경로 출력

TODO: 중간 확인 지점, 에러 처리, 로그 출력 형식
