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

## 현재 상태

골격만 있고 실제 문서는 점진적으로 추가됨. 각 폴더의 `.gitkeep`은 문서 들어오면 삭제.

## 규모 한계

이 단순 폴더 RAG 방식의 적정 규모는 **문서 100개 이하**. 100~500개 시 검색 속도 저하, 500개 이상 시 임베딩 기반 RAG(Dify/AnythingLLM 등)로 갈아탈 것을 권장.
