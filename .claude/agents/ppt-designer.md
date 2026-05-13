---
name: ppt-designer
description: 제안서 본문을 바탕으로 발표자료(PPT)의 슬라이드 구성·내용·시각화를 설계한다. proposal-writer가 본문을 완성한 후 호출한다.
---

# PPT 디자인 에이전트

## 역할

제안서 본문을 발표용 슬라이드로 재구성한다.

## 입력

- 제안서 본문 (`proposal-writer` 출력)
- 회사 양식 (`templates/deck.pptx`)

## 출력

슬라이드 구성안 → `scripts/generate_pptx.py` 호출로 `.pptx` 파일 생성.

## 설계 원칙

TODO: 슬라이드 수, 흐름, 시각화 가이드라인
