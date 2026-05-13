# DSI Smoke Test — 2026-05-13

자율 모드 동안 시스템 end-to-end 동작 검증.

## 입력

- 샘플 RFP: `examples/sample-rfp.md` (가상공항 실내 내비게이션 시스템 구축, 가공 데이터)

## 검증한 워크플로우

```
샘플 RFP (.md)
   ↓ rfp-analyst (korean-public-rfp skill 활용)
analysis.yaml                                    [✓]
   ↓ proposal-writer (proposal-korean-style skill 활용)
proposal_가상공항IT_v1.md                        [✓]
   ↓ scripts/md2docx.py (Korean-safe python-docx)
proposal_가상공항IT_v1.docx                      [✓]
   ↓ ppt-designer (ppt-presentation-structure skill 활용)
slides_가상공항IT_v1.yaml                        [✓]
   ↓ scripts/yaml2pptx.py (Korean-safe python-pptx)
발표자료_가상공항IT_v1.pptx                      [✓]
```

## 산출물 (output/20260513/, gitignore됨)

| 파일 | 크기 | 비고 |
|---|---|---|
| `analysis.yaml` | 4.5KB | RFP 분석, 누락·위험 표기 포함 |
| `proposal_가상공항IT_v1.md` | 6.7KB | 제안서 본문 마크다운 |
| `proposal_가상공항IT_v1.docx` | 40KB | Word 파일, 표·헤딩·리스트 한국어 OK |
| `slides_가상공항IT_v1.yaml` | 11KB | 22슬라이드 구성안, 발표자 노트 포함 |
| `발표자료_가상공항IT_v1.pptx` | 70KB | PowerPoint 파일, 한국어 OK |

## 검증된 사항

- ✓ 한국어 .docx 생성·읽기 (헤딩·본문·표)
- ✓ 한국어 .pptx 생성·읽기 (표지·본문·발표자 노트)
- ✓ RFP에서 누락 항목·위험 신호 검출 (skill 동작)
- ✓ 평가배점 → 슬라이드 분량 매핑 (25점 추진방안에 30% 비중)
- ✓ TODO 표시로 KB 미확보 정보 명시 (추측 금지 규칙 준수)
- ✓ 자체 검토 체크리스트 적용 (모든 평가항목 본문에서 다룸 등)

## 미검증·한계

- ⚠ 회사 양식(`templates/proposal.docx`, `deck.pptx`) 미적용 — 양식 도착 후 디자인 통일 필요
- ⚠ KB 자료 미확보 — 회사 소개·실적·기술 부분 TODO 표시로 처리 (실제 데이터 들어오면 자동으로 풍부해짐)
- ⚠ 공식 docx/pptx skill (Anthropic 제공)은 pandoc·libreoffice 필요 — 현재 환경에 미설치라 자체 변환기(scripts/md2docx.py, yaml2pptx.py)로 우회
- ⚠ End-to-end는 *수동 단계 분할*로 검증. 실제 `/rfp` 슬래시 명령 한 번에 전 단계 실행은 Claude Code 인터랙티브 세션에서 별도 검증 필요

## 도구 의존성 확인

| 도구 | 상태 |
|---|---|
| `python3` 3.11 | ✓ |
| `python-docx` 1.2.0 | ✓ |
| `python-pptx` 1.0.2 | ✓ |
| `pyyaml` | ✓ |
| `pandoc` | ✗ (있으면 더 풍부한 변환 가능) |
| `libreoffice` | ✗ (있으면 .doc/.docx, .pptx 검증 강화) |

## 다음 단계 제안

1. KB 자료 도착 후 `dabeeo-profile/SKILL.md` 채우기
2. 회사 양식 파일 `templates/` 도착 후 변환기에 양식 적용 로직 추가
3. 실제 사내 RFP 1건으로 end-to-end 재검증
4. (선택) Eval 셋업으로 skill 품질 정량화

## 결론

**시스템 골격이 end-to-end로 동작함.** 한국어 처리·구조 매핑·자체 검토 모두 정상.
회사 자료(KB·양식)가 들어오면 즉시 실사용 가능한 상태.
