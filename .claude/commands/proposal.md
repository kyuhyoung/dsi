---
description: 이미 작성된 제안서 파일(.md/.docx/.hwp/.hwpx/.pdf)을 입력으로 발표자료(.pptx) 생성. RFP 분석·본문 작성 단계를 스킵하고 ppt-designer부터 시작한다.
---

# /proposal 명령

## 사용법

```
/proposal <제안서 파일 경로>
```

예시:
```
/proposal output/20260514/제안서_피지컬AI_v1.md
/proposal ~/Downloads/제안서_사업명.docx
/proposal samples/proposals/회사_제안서.hwp
```

지원 포맷: `.md`, `.txt`, `.docx`, `.hwp`, `.hwpx`, `.pdf`

## 동작 흐름 (4단계, 검토 지점 2개)

### 0단계: template 자동 점검 (조용히)

빌드 전 *template style.yaml* 점검:
- `templates/*.pptx` 중 `.style.yaml` 없거나 오래된 것 발견
- 발견 시 사용자에게 안내: *"새 template 발견: <name>. /onboard-template 실행 권장."*
- 이미 모든 template 등록됨 → 스킵

기존 등록 template만 사용할 거면 0단계 알림 무시 가능.

### 1단계: 텍스트 추출

```
python3 scripts/extract_proposal.py <파일경로> output/<YYYYMMDD>/제안서_<사업명>.txt
```

- 포맷별 추출:
  - `.md/.txt` → 그대로
  - `.docx` → python-docx (헤딩·표 보존)
  - `.hwp` → `hwp5txt` CLI (pyhwp 패키지)
  - `.hwpx` → zipfile + XML 파싱
  - `.pdf` → `pdftotext -layout` 또는 pdfplumber

- 추출 실패 시 즉시 사용자에게 보고 + 수동 변환 안내 (HWP→PDF→재시도 등)

### 2단계: 사업명·발주처·제안사 추출 + 사용자 확인

추출된 텍스트 첫 1~2 페이지에서 다음 메타데이터 식별:

- **사업명** — 보통 표지에 큰 글씨 또는 "사업명:" 라벨
- **발주처** — "발주기관"·"수요기관"·"의뢰처" 키워드
- **제안사** — "제안사"·"수행기관" 키워드 또는 사용자에 질문

식별 결과를 사용자에게 보여주고 *진행 전 승인* 받기. 사용자가 보정 가능.

### 3단계: ppt-designer 호출 → 슬라이드 yaml

**3-A. 사용할 template 결정** (4-1단계의 `--template` 인자 미리 확정)

`templates/*.pptx` 파일 중 사용할 template을 결정. 1개면 자동, 여러 개면 사용자 선택.

이 template은 *외형(tone & manner)* 만 가져옴. 챕터 구성·발표 흐름에 영향 없음 (CLAUDE.md "Template은 껍데기다" 원칙).

**3-B. visual element schema 확인**

- `templates/visual_element_schema.yaml` 의 각 type 키 정의를 ppt-designer가 *반드시 따른다* (특히 flow_arrow=items 같은 정확한 키 사용)

**3-C. `ppt-designer` 에이전트 호출**

전달할 입력:
- 추출된 제안서 텍스트
- 메타데이터 (사업명·발주처·제안사·일자)
- `ppt-presentation-structure` 스킬 참조 강제
- `templates/visual_element_schema.yaml` 참조 강제

**template chapters 정보는 *전달하지 않음*.** 콘텐츠 흐름은 제안서가 결정.

에이전트가 출력해야 할 yaml:

- 종류=표지·목차·간지·회사소개·본문·결론·감사 적절히 사용
- **간지 개수 == 목차 섹션 개수** (제안서 흐름이 결정)
- 간지의 `장이름` = *콘텐츠 의도대로* (template chapters와 무관)
- 본문·결론·부록의 `장번호` 100% 명시 (정수, 직전 간지와 동일)
- 시각요소는 schema yaml의 정확한 키 사용 (`items`, `categories`, `series` 등)
- 결과는 `output/<YYYYMMDD>/slides_<사업명>_v1.yaml` 에 저장

**여기서 사용자 검토 지점 (.pptx 빌드 전 yaml 확인).**

### 4단계: 빌드 + PDF 변환 + 결과 보고

**4-1. .pptx 빌드**

```
python3 scripts/yaml_to_pptx.py \
    output/<YYYYMMDD>/slides_<사업명>_v1.yaml \
    output/<YYYYMMDD>/발표자료_<사업명>_v1.pptx \
    --template <회사_템플릿_이름>
```

`--template` 인자 결정:
- `templates/*.pptx` 파일 1개면 자동 선택
- 여러 개면 사용자에게 선택 요청
- 0개면 default (Dabeeo) 사용

**4-2. .pdf 자동 변환 (필수)**

빌드 성공 시 자동으로 LibreOffice headless 호출:

```
"/mnt/c/Program Files/LibreOffice/program/soffice.exe" \
    --headless --convert-to pdf \
    --outdir output/<YYYYMMDD>/ \
    output/<YYYYMMDD>/발표자료_<사업명>_v1.pptx
```

(Linux: `libreoffice` / WSL: 위 Windows 경로 또는 `soffice` 자동 탐지)

LibreOffice 없으면 *경고 출력 + .pptx만 산출*. PDF 생성 실패해도 빌드 자체는 성공.

**4-3. 자동 시각 검증 (필수)**

PDF 생성 후 *visual-validator subagent 자동 호출*:

```
mkdir -p /tmp/validate_<name>
pdftoppm -png -r 80 output/<YYYYMMDD>/발표자료_<사업명>_v1.pdf /tmp/validate_<name>/p
```

그 후 `visual-validator` 에이전트 호출 — 모든 슬라이드 PNG를 *직접 보고* `templates/visual_validation_checklist.yaml` 의 8개 카테고리로 검증.

발견 정책:
- **critical** (텍스트 겹침·콘텐츠 누락) → 사용자에게 보고, *수정 후 재빌드 결정 받음*
- **high** (잘림·라벨 오류) → 보고만, 사용자 결정
- **medium** (가독성·일관성) → 보고만

수정 방향이 *빌더·style.yaml·콘텐츠 yaml* 중 어느 쪽 책임인지 명시.

**4-4. 결과 보고**

- `.pptx` 경로
- `.pdf` 경로
- 시각 검증 요약 (critical/high/medium 개수)
- 슬라이드 수·간지 개수·경고 메시지
- 사용된 템플릿 이름

**4-5. (선택) /preview 안내**

추가 시각 검토하고 싶으면 `/preview <pptx 경로>` 권장.

## RFP 시작 vs 제안서 시작 비교

| 흐름 | 명령 | 단계 | 산출물 |
|---|---|---|---|
| RFP에서 시작 | `/rfp <RFP>` | 분석→본문→PPT (7단계) | `.docx` + `.pptx` |
| 제안서에서 시작 | `/proposal <제안서>` | 추출→PPT (4단계) | `.pptx` 만 |

제안서를 이미 가지고 있는 경우는 본 명령이 훨씬 빠릅니다.

## 주의

- 사업명·발주처가 제안서에서 자동 추출 안 되면 사용자에게 질문해서 입력 받기
- HWP 변환 시 표·그림은 텍스트로만 추출됨 → 시각요소는 ppt-designer가 본문 내용 기반으로 *재구성*해야 함 (원본 그림은 못 옮김)
- 제안서가 50페이지 이상이면 ppt-designer 입력 토큰 초과 가능 → 섹션별 분할 처리 고려
