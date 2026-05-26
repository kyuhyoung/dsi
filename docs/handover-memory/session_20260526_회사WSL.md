# 세션 인수인계 — 2026-05-26 회사 WSL → PowerShell

회사 PC WSL 세션 → PowerShell native (한컴 2018 설치 완료) 이전용 스냅샷.

## 이 세션이 한 변경 (git 반영 완료)

| commit | 내용 |
|---|---|
| `95db14a` | `restore_memory` slug 자동 감지 (집·WSL·macOS 호환) |
| `a6468ae` | CHECKBOX_RE 확장 — 긴 라벨·괄호·줄바꿈·☒ 변형 모두 식별 (신청유형 ☑ 미표시 fix) |
| `e82dca7` | EXAMPLE_RE 에서 ↳ 제거 → SUBORDINATE_RE 가 처리 (한국 양식 관행) |

## 검증 결과 (회사 WSL — 데이터·알고리즘 수준)

### 셀 매핑 오차 — *완전 0*
- 본체별지 셀 id (T*): 358/358 매칭, 0 오차
- 단락 id (P*): 54/54 매칭, 0 오차
- 셀 안 단락 id (T*_P*): 13/13 매칭, 0 오차

### Under-fill 13 분석
- 의도적 skip 7 (T20·T24·T27·T34·T51·T54·T59 — 섹션 헤더 옆 빈 셀)
- 의도적 skip 4 (example 셀 — 양식 예시)
- 맥락 없음 1 (T50_R0_C0 — hint 전부 비어있음)
- **검토 필요 1** (T16_R2_C0 — 단독 신청 시 "해당 없음" 명시 vs 비워두기)

### intent 분류 알고리즘 일반성
- 26년 민군·F16PBU 양식에 같은 알고리즘 돌려 동작 — 일반 ✓
- 농식품AI 만 트리거되는 패턴은 *추가 룰 박지 않음* (overfit 회피)

## 남은 갭 — 집/PowerShell + 한컴 필요

| 갭 | 진단 도구 |
|---|---|
| 신청유형 ☑ 미표시 fix 검증 | 농식품AI .hwp → .hwpx 재추출 → form.yaml의 신청유형 셀 intent 확인 |
| 일부 셀 매핑 시각 어긋남 (집에서 보고됨) | `fill_hwpx_form.py` 결과 .hwpx → 한컴 SaveAs .hwp → PDF 시각 확인 |
| 빈 셀 hp:t 신설 한컴 PDF render 한계 | 한컴 PDF render 디버깅 — XML 구조 vs 실제 render |
| T16_R2_C0 단독신청 "해당 없음" 적합 여부 | 사용자 결정 |

## 새 세션 첫 명령 (PowerShell에서)

```powershell
cd D:\work\dabeeo\dsi
chcp 65001
.\install.ps1                       # pywin32 확인·설치
.\scripts\restore_memory.ps1        # 메모리 복원
claude                              # Claude Code 시작
```

Claude에 한 마디:

> "회사 PC에 한컴 2018 깔았다. WSL → PowerShell 이전. `docs/handover-memory/session_20260526_회사WSL.md` 읽고 이어서 진행. 우선 신청유형 ☑ 미표시 fix 검증부터 (농식품AI .hwp → .hwpx 재추출 → 셀 intent 확인)."

## 도구 호출 흐름 (한컴 동작 확인)

```powershell
# 1. 한컴 COM 동작
python -c "import win32com.client; h=win32com.client.Dispatch('HWPFrame.HwpObject'); print(h.Version); h.Quit()"

# 2. .hwp → .hwpx
python scripts/hwp_to_hwpx.py "samples/rfp_downloaded/[양식] 농식품 분야 「AI 응용제품 신속상용화 지원사업」.hwp" output/<날짜>/통합양식.hwpx

# 3. 양식 분석 (.hwpx → form.yaml — 새 CHECKBOX_RE·↳ 분류 적용된 결과)
python scripts/extract_hwpx_form.py output/<날짜>/통합양식.hwpx output/<날짜>/통합양식.form.yaml

# 4. 신청유형 셀 intent 확인 (T16_R0_C1, T16_R0_C3 가 checkbox 로 분류되는지)
python -c "
import yaml
with open('output/<날짜>/통합양식.form.yaml') as f: form = yaml.safe_load(f)
for t in form['tables']:
    if t['idx'] == 16:
        for c in t['cells']:
            print(c['id'], c['intent'], repr(c['text'][:50]))
"
# 기대: T16_R0_C1·T16_R0_C3 intent = checkbox (이전엔 label_or_content 오분류)
```

## 작업 환경 분업 권장

- **PowerShell + Windows python**: 한컴 COM + 모든 파이프라인 (`hwp_to_hwpx`·`extract_hwpx_form`·`fill_hwpx_form`·`split_hwp_by_section_macro`)
- **WSL** (보조): git/grep/sed 같은 Linux tool, 또는 그냥 닫음

## Untracked 파일 (push 안 됨)
- `samples/rfp_downloaded/농식품AI_양식.form.v1.yaml.bak` (이전 form.yaml 백업, 보존만)
