---
description: RFP 파일 경로를 받아 분석 → 제안서(.docx) → 발표자료(.pptx) 까지 생성한다. 단계마다 사용자 검토를 받고 진행한다.
---

# /rfp 명령

## 사용법

```
/rfp <RFP 파일 경로>
```

예시:
```
/rfp ~/Downloads/공항IT_2024.pdf
/rfp ./examples/sample-rfp.pdf
```

## 동작 흐름 (6단계, 검토 지점 3개)

### 0단계: template 자동 점검 (조용히)

빌드 전 *template style.yaml* 점검:
- `templates/*.pptx` 중 `.style.yaml` 없거나 오래된 것 발견
- 발견 시 사용자에게 안내: *"새 template 발견: <name>. /onboard-template 실행 권장."*
- 모든 template 등록 상태 → 스킵


### 1. RFP 분석
- `rfp-analyst` 에이전트 호출
- 파일 읽고 구조화된 YAML 생성

### ✋ 검토 지점 1
사용자에게 분석 결과 표시, 검토 후 *진행* 응답 대기:
- 누락 항목 / 위험 신호가 있으면 강조 표시
- 사용자 피드백·수정 요청 반영 후 다음 단계

### 2. 제안서 본문 작성
- `proposal-writer` 에이전트 호출
- `kb/` 검색하며 본문 마크다운 작성

### ✋ 검토 지점 2
사용자에게 본문(.md) 표시, *진행* 응답 대기:
- 톤·내용·평가항목 매핑 점검
- 수정 요청 반영 후 다음 단계

### 3. Word 출력
- 공식 `docx` skill 호출
- `output/<YYYYMMDD>/제안서_<사업명>_v<버전>.docx` 생성
- 파일 경로 출력

### 4. 슬라이드 구성
- *template 결정*: 사용할 `templates/<name>.pptx` 결정 (5단계의 `--template` 인자 미리 확정). template은 *외형만* 제공 (CLAUDE.md "Template은 껍데기다" 원칙).
- `templates/visual_element_schema.yaml` 참조 (시각요소 키 정확)
- `ppt-designer` 에이전트 호출 — *visual schema*만 입력으로 전달. **template chapters는 전달 안 함** (콘텐츠 흐름은 제안서가 결정).
- 제안서 본문 기반 YAML 구성안 작성 — 챕터 구성은 자율.

### ✋ 검토 지점 3
사용자에게 구성안(.yaml) 표시, *진행* 응답 대기:
- 슬라이드 흐름·시간 배분 점검
- 수정 요청 반영 후 다음 단계

### 5. PPT 출력
- `scripts/yaml_to_pptx.py` 호출 → `output/<YYYYMMDD>/발표자료_<사업명>_v<버전>.pptx`
- 빌드 성공 시 LibreOffice headless로 *자동 PDF 변환*:
  ```
  "/mnt/c/Program Files/LibreOffice/program/soffice.exe" \
      --headless --convert-to pdf \
      --outdir output/<YYYYMMDD>/ \
      output/<YYYYMMDD>/발표자료_<사업명>_v<버전>.pptx
  ```
  (Linux: `libreoffice` 또는 `soffice`. 없으면 PDF 스킵 + 경고)

### 5-1. 자동 시각 검증 (필수)

PDF 생성 후 *visual-validator subagent 자동 호출*. 모든 슬라이드 PNG를 직접 보고 `templates/visual_validation_checklist.yaml` 의 8개 카테고리로 검증.

- **critical** (텍스트 겹침·콘텐츠 누락) → 사용자에게 보고, 수정 후 재빌드 결정 받음
- **high·medium** → 보고만, 사용자 결정

### 6. 결과 보고

모든 산출물 경로를 정리해 출력:
```
완료. 산출물:
- output/<YYYYMMDD>/analysis.yaml
- output/<YYYYMMDD>/제안서_<사업명>_v<버전>.docx
- output/<YYYYMMDD>/발표자료_<사업명>_v<버전>.pptx
- output/<YYYYMMDD>/발표자료_<사업명>_v<버전>.pdf       # 자동 변환
```

(선택) 시각 검토하고 싶으면 `/preview <pptx 경로>` 안내.

## 출력 폴더 구조

```
output/<YYYYMMDD>/
├── analysis.yaml                    # rfp-analyst 결과 (재현용)
├── 제안서_<사업명>_v<버전>.md       # 본문 마크다운
├── 제안서_<사업명>_v<버전>.docx
├── slides_<사업명>_v<버전>.yaml     # ppt-designer 구성안
├── 발표자료_<사업명>_v<버전>.pptx
└── 발표자료_<사업명>_v<버전>.pdf    # LibreOffice 자동 변환
```

같은 사업명 재실행 시 버전 자동 증가 (v1 → v2 → v3).

## 에러 처리

| 상황 | 대응 |
|---|---|
| 파일 못 읽음 | 경로·형식 재확인 요청 |
| 사업명 추출 실패 | 사용자에게 직접 입력 요청 |
| KB 검색 결과 빈약 (3건 미만) | 사용자에게 알림, 진행 여부 확인 |
| docx/pptx skill 호출 실패 | 오류 메시지 그대로 보고, 재시도 여부 확인 |
| 사용자 검토 단계에서 *중단* 응답 | 현재까지 산출물만 저장하고 종료 |

## 진행 상황 로그

각 단계 시작·완료 시 한 줄 로그 출력:

```
[1/6] RFP 분석 중... (파일: <경로>)
[1/6] 분석 완료. ✋ 검토 요청.
[2/6] 본문 작성 중... (KB 검색: kb/projects/, kb/company/)
[2/6] 본문 작성 완료. ✋ 검토 요청.
[3/6] .docx 생성 중...
[3/6] .docx 생성 완료: output/20260513/제안서_공항IT_v1.docx
[4/6] 슬라이드 구성 중...
[4/6] 슬라이드 구성 완료. ✋ 검토 요청.
[5/6] .pptx 생성 중...
[5/6] .pptx 생성 완료: output/20260513/발표자료_공항IT_v1.pptx
[6/6] 완료.
```

## 사용자 응답 약속

각 검토 지점에서 사용자가 입력할 수 있는 응답:

- `진행` / `다음` / `ok` — 다음 단계로
- `수정: <내용>` — 현재 단계 결과를 수정 요청
- `중단` / `종료` — 현재까지 결과만 저장하고 종료
