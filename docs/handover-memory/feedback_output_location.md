---
name: 결과물은 프로젝트 output 폴더에
description: PoC·중간 산출물도 C:\Temp 같은 시스템 임시 폴더가 아니라 D:\work\dabeeo\dsi\output\<날짜>\ 에 저장. 사용자가 못 보면 의미 없음.
type: feedback
originSessionId: 9831bd2c-c977-4c8a-b8a9-4b875d797ede
---
**원칙 (사용자 확정 2026-05-25)**: *"결과는 사용자가 찾을 수 있는 곳에 저장. Temp 폴더 X."*

**Why**: PoC #16 결과를 `C:\Users\kevin\AppData\Local\Temp\` 에 저장 → 사용자가 "어떻게 보라고" 항의. 시스템 임시 폴더는 사용자 시야 밖.

**How to apply**:
- 모든 산출물 (PoC·중간·최종) → `D:\work\dabeeo\dsi\output\<YYYYMMDD>\` 에 저장
- 파일명 규칙: `PoC_<기능>.<ext>`, `<단계>_<사업명>_v<N>.<ext>` 등 의미 있게
- `/tmp/` 또는 `Temp/` 는 *진단·내부 변환* 같은 *버려도 되는 작업물*에만
- 매 결과 후 사용자에게 *프로젝트 경로* 로 알림
