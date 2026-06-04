---
name: dabeeo-profile
description: 제안사(회사 KB에 정의된 회사)의 회사 정보·주요 실적·보유 기술·인증 참조 시 적용. 제안서의 회사 소개·사업 수행 역량·경쟁사 대비 차별점 작성에 사용. 현재 제안사 = 다비오.
---

# 제안사 회사 프로필 — KB 라우팅

본 skill 은 *회사 무관 라우팅·사용 지침*만 보유한다. **회사 특정 정보(메타데이터·실적·기술·차별점·핵심 메시지)는 skill·코드에 박지 않고 `kb/` 의 KB 파일에 두며, `Glob`/`Grep` 으로 자동 활용**한다. 제안사 교체 = KB 폴더 교체이며 *본 skill·정책·코드 수정 0* 이어야 한다 (임의 회사 일반화).

## 현재 제안사 = 다비오 (Dabeeo)

- 회사 KB: **`kb/company/dabeeo/`** (`profile.yaml` · `finance.yaml` · `quantitative.md` · `intro.md` · `tech-core.md` 등)
- 핵심 수치·실적·기술·차별점·메시지 톤은 *그 KB 파일에서* 검색한다 — 본 skill 에 요약·수치를 박지 않는다 (회사 교체 시 md 수정이 생기면 overfit).

## KB 라우팅

| 필요 정보 | 검색 위치 |
|---|---|
| 회사 일반·인증·자격·**실적·기술** | `kb/company/{회사}/` (회사별 분리 — 그 회사 자료 전부 이 폴더 안) |
| 과거 제안서 (참고, 회사 무관) | `kb/proposals/` |

> 회사 자료는 *전부* `kb/company/{회사}/` 아래 (예: `dabeeo/projects.md`·`tech-core.md`, `lig/projects/`·`tech/`). 공용 `kb/projects/`·`kb/tech/` 폴더는 폐지 — 회사별 폴더로 분리됨.

절차: `Glob "kb/company/{회사}/**/*"` 로 *그 회사 폴더 범위만* 파악 → `Grep "<키워드>"` 매칭 → `Read` → 인용 시 *KB 파일 경로*를 출처로 명시. (다른 회사 폴더는 검색 안 함 — 혼입 방지.)

## 사용 지침 (proposal-writer 등 agent)

1. 회사 정보는 *KB 파일에서 검색* — 본 skill 본문에 회사 수치를 박아 인용하지 않는다.
2. 인용 시 출처(KB 경로) 명시 (예: `(kb/company/dabeeo/quantitative.md §6)`).
3. KB 미수록 사항 → `(확인 필요)` (추측·창작 금지).
4. 격식체·문체 — `proposal-korean-style` skill.

## 제안사 교체 절차 (담당자)

새 제안사 자료가 오면 `kb/company/{회사}/` 아래에 저장 (실적·기술도 그 폴더 안 — 예: `projects.md`/`projects/`, `tech-core.md`/`tech/`; 각 파일 상단 frontmatter `title`·`client`·`keywords`·`source` 필수). `Glob`/`Grep` 으로 자동 활용 — **본 skill 수정 불필요**. 회사명만 바뀌면 위 "현재 제안사" 한 줄만 갱신.

> **회사별 분리 완료**: 이전 LIG D&A 데모 데이터(천궁·현궁·정밀유도무기)는 `kb/company/lig/` 아래로 이동됨(`lig/projects/`·`lig/tech/`). 다비오는 `kb/company/dabeeo/`. 제안사 검색을 *해당 회사 폴더 범위*로 한정하므로 회사 간 혼입 없음. (LIG 데모는 다른 회사 KB 교체가 정상 동작하는지 검증한 흔적 — 보존하되 분리됨.)
