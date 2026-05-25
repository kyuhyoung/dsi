---
name: 양식 채움은 XML 결정적 편집
description: .hwpx XML 직접 편집으로 빈 셀 채움. 한컴 COM은 .hwp↔.hwpx 변환 도구로만 1회 사용. 한컴 COM 연속 호출은 비결정성 위험.
type: feedback
originSessionId: 9831bd2c-c977-4c8a-b8a9-4b875d797ede
---
**원칙 (사용자 확정 2026-05-24, 근본 치유 4차)**: *"채움은 XML 결정적 편집. 한컴 COM은 변환 도구로만."*

**Why**: 근본 치유 3차에서 HwpObject COM 으로 셀 단위 채움 시도 → *비결정적 동작* 관찰. 5fill 테스트는 동작, 661fill 풀 실행은 ○가 표 안에 안 박힘 (위치 누적 또는 명령 무시). 진단 결과 한컴 인스턴스의 *전역 상태 카리오버* 가 원인. 임의 양식 100% 보장 불가.

**How to apply**:
- **변환만 한컴 COM**: 양식이 .hwp 면 `scripts/hwp_to_hwpx.py` 가 *1회* HwpObject 호출로 .hwpx 변환. 그 외 fill 작업은 한컴 일체 안 거침.
- **채움은 XML 편집**: `scripts/fill_hwpx_form.py` 가 .hwpx zip 풀어 section*.xml 의 `<hp:tc>` (table cell) 안 `<hp:p><hp:run><hp:t>` 노드에 텍스트만 박음. zip 다시 묶음. 양식 visual·border·서식·도형·이미지 *일체 미변경*.
- **추출도 .hwpx 기반 일원화**: `extract_hwp_form.py` → `extract_hwpx_form.py`. 일관된 XML 좌표계. hwp5proc XML과 .hwpx XML 두 스키마 동시 유지 금지.
- **양식 형식 무관**: 입력 양식이 .hwp 든 .hwpx 든 동작. .hwp 면 자동 .hwpx 변환 후 처리.
- **한컴 미설치 PC**: .hwpx 양식만 받으면 한컴 없이도 fill 가능 (cross-platform).
