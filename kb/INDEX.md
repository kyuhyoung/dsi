# DSI Knowledge Base — Index

다비오 사내 지식베이스. RFP 제안서·발표자료 작성 시 Claude가 참조하는 회사 자산.

## 폴더 구조

| 폴더 | 들어가는 것 | 예시 파일명 |
|---|---|---|
| `company/` | 회사 정보, 인증, 자격 | `intro.md`, `certifications.md`, `financials.md` |
| `projects/` | 과거 프로젝트 실적 | `2024-incheon-airport.md`, `2023-kac.md` |
| `proposals/` | 과거 제안서 (참고용) | `rfp-2024-001/proposal.md` (+ `meta.yaml`) |
| `tech/` | 기술 자료, 보유 기술 명세 | `indoor-positioning.md`, `ar-navigation.md` |

## 파일 형식 규칙

- 우선 `.md` 사용 (Claude가 가장 잘 다룸)
- 원본이 `.pdf`/`.docx`면 그대로 둬도 됨 (Claude Code Read tool이 직접 파싱)
- 각 파일 상단에 메타데이터 권장:

```yaml
---
title: 인천국제공항 IT 인프라 구축
period: 2024-03 ~ 2024-12
client: 인천국제공항공사
budget: 약 OO억
keywords: [공항, IT인프라, 실내측위, AR]
---
```

## 검색 방식 (Claude 동작)

1. `Glob "kb/**/*.md"` — 구조 파악
2. `Grep "<키워드>" kb/` — 키워드 매칭
3. `Read` — 매치된 파일 읽기
4. 인용 시 파일 경로를 출처로 명시

## 검색 키워드 팁

- 사업명·발주처명: "인천공항", "공항공사", "한국전력" 등
- 분야: "공항 IT", "실내 측위", "AR 안내" 등
- 시기: "2024", "최근 3년" 등

## 회사별 폴더 구조 (`company/`)

`company/` 하위는 회사 단위로 정리된다. 현재 보유 중인 회사 KB:

| 회사 폴더 | 설명 | 보유 문서 |
|---|---|---|
| `company/dabeeo/` | **다비오 (제안사 본인)** — 회사소개자료.pptx에서 추출 (+ D 사업계획서 보강) | `intro.md`, `history.md`, `investment.md`, `organization.md`, `certifications.md`, `tech-core.md`, `business.md`, `projects.md`, `quantitative.md` |
| `company/lig/` | **LIG넥스원 (전략적 투자사·방산 파트너)** — 협력 컨텍스트 참고용 | `intro.md`, `certifications.md`, `financials.md`, `rd-capability.md` |

### `company/dabeeo/` 섹션 색인

| 파일 | 다루는 내용 | 출처 슬라이드 |
|---|---|---|
| `intro.md` | 회사 개요·정체성 (GeoAI 전문기업, AI 기반 Earth Intelligence) | 1·3·4·40 |
| `history.md` | 연혁 (2012 설립 → 투자유치 → 인증·수상 → 글로벌 확장) | 4 |
| `investment.md` | 누적 369억원 투자 (KORINDO·LIG넥스원 등 라운드별) | 5·6 |
| `organization.md` | 조직·해외법인 (인니·미국·베트남 Vina 데이터랩) | 4·27 |
| `certifications.md` | 인증·수상 (CES 혁신상·미래유니콘·이노비즈·TTA·ISO27001 등) | 4·7·28·29·30·31·32 |
| `tech-core.md` | 6대 핵심 기술 (Super Resolution·Image Alignment·Semantic Segmentation·Object Detection·Change Detection·3D Reconstruction) + Eartheye 플랫폼 | 12~26 |
| `business.md` | 사업 영역 (공간·인프라·국방·임농업·기후) + 구독형 전환 로드맵 | 34·39·40 |
| `projects.md` | 주요 프로젝트·고객 (카카오·네이버·TMAP·한국자산관리공사·국방과학연구소·KORINDO·Salim 등) | 4·22·23·25·26·35·36·37·38 |
| `quantitative.md` | **D 보강** — Eartheye Plantation 정량 지표 (F1 0.98·생산성 12%·연 610억·1000㎢ 345→29일·팜오일 110조·정밀농업 CAGR 11.6%·GPU·연구인력 64명·정부과제 29건·112.4억·수상 13건·산학협력 9개교 등) | D 사업계획서 |

대부분의 다비오 KB 문서의 출처는 `templates/[다비오] 회사소개자료.pptx` (2026.02 버전, 41 slides). 단, `quantitative.md`는 `samples/proposals/[2차취합]_사업계획서.txt` (사용자 작성 D 문서)에서 추출한 정량 지표 보강 KB.

## 현재 상태

골격만 있고 실제 문서는 점진적으로 추가됨. 각 폴더의 `.gitkeep`은 문서 들어오면 삭제.

## 규모 한계

이 단순 폴더 RAG 방식의 적정 규모는 **문서 100개 이하**. 100~500개 시 검색 속도 저하, 500개 이상 시 임베딩 기반 RAG(Dify/AnythingLLM 등)로 갈아탈 것을 권장.
