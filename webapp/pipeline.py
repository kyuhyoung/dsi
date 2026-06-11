# -*- coding: utf-8 -*-
"""
DSI 풀 생성 웹앱 백엔드 — pipeline.py

회사 + RFP(공고+양식) + 비즈니스 결정 → 제안서 .hwpx/.pdf 를 생성한다.

Claude Code 의 subagent(rfp-analyst·proposal-writer)는 파일시스템 도구(Read/Grep/Glob)로
KB·양식을 탐색하지만, 웹앱은 Anthropic API 단발 호출이라 *파일 탐색 도구가 없다*.
따라서 이 모듈이 KB·양식·skill 정책을 *프롬프트에 모아 넣는다* (안정부는 prompt caching).

정책 정본은 .claude/agents/*.md, .claude/skills/*/SKILL.md — 여기서 *로드*만 한다.
회사·RFP·양식은 전부 변수 — 특정 회사/사업 키워드를 이 코드에 박지 않는다.

두 LLM 호출:
  (1) rfp-analyst    — RFP 본문 + form.yaml          → rfp_analysis.yaml
  (2) proposal-writer — form.yaml + rfp_analysis + KB + 결정 → fills.yaml(빈칸 채움)

결정적 단계(회사메타·재무·사업비 채움, 양식 변환·추출, 빌드·분할·PDF)는
기존 scripts/ 를 subprocess 로 호출 — 재구현하지 않는다.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yaml

try:
    import anthropic
except ImportError:  # 친절한 안내 — Streamlit 쪽에서 잡아 표시
    anthropic = None

# ── 경로 상수 ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
KB_COMPANY = ROOT / "kb" / "company"
AGENTS = ROOT / ".claude" / "agents"
SKILLS = ROOT / ".claude" / "skills"
SAMPLES = ROOT / "samples" / "rfp_downloaded"
OUTPUT = ROOT / "output"

MODEL = "claude-opus-4-8"  # claude-api skill 기본값. 변경은 사용자 결정.

# rfp-analyst → korean-public-rfp,  proposal-writer → proposal-korean-style + dabeeo-profile(라우팅)
ANALYST_SKILLS = ["korean-public-rfp"]
WRITER_SKILLS = ["proposal-korean-style", "dabeeo-profile"]

# 입력 포맷 분류 (UI 드롭다운 후보 필터링용)
RFP_EXTS = {".hwp", ".hwpx", ".pdf", ".docx"}
FORM_EXTS = {".hwp", ".hwpx", ".docx"}


# ── 진행 로그 ──────────────────────────────────────────────────────────────
ProgressFn = Callable[[str], None]


def _noop(_msg: str) -> None:
    pass


# ── 기본 유틸 ──────────────────────────────────────────────────────────────
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _env() -> dict:
    """subprocess 용 — 자식 파이썬도 UTF-8 로 입출력하게 강제 (Windows cp949 회피)."""
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    return e


def run_script(args: list[str], log: ProgressFn = _noop, timeout: int = 1200) -> str:
    """scripts/ 의 파이썬을 호출. 실패 시 stderr 를 담아 예외."""
    cmd = [sys.executable] + [str(a) for a in args]
    log(f"$ {' '.join(Path(c).name if SCRIPTS.as_posix() in str(c) else str(c) for c in cmd)}")
    proc = subprocess.run(
        cmd, cwd=str(ROOT), env=_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-1500:]
        raise RuntimeError(f"스크립트 실패 (exit {proc.returncode}): {Path(args[0]).name}\n{tail}")
    return proc.stdout


# ── 카탈로그 (UI 드롭다운) ─────────────────────────────────────────────────
def list_companies() -> list[str]:
    """profile.yaml 을 가진 회사 폴더 = 제안 가능한 제안사."""
    if not KB_COMPANY.exists():
        return []
    return sorted(
        d.name for d in KB_COMPANY.iterdir()
        if d.is_dir() and (d / "profile.yaml").exists()
    )


PROJECTS_YAML = Path(__file__).resolve().parent / "projects.yaml"


def list_projects() -> list[dict]:
    """과제 목록 — webapp/projects.yaml 에 정의된 (name, rfp, form). 사용자는 name 만 고른다.

    rfp/form 파일이 둘 다 samples/rfp_downloaded/ 에 있어야 노출(없으면 자동 숨김).
    과제 추가 = projects.yaml 한 항목 추가 — 코드 수정 0.
    """
    if not PROJECTS_YAML.exists():
        return []
    try:
        data = yaml.safe_load(_read(PROJECTS_YAML)) or {}
    except Exception:
        return []
    out = []
    for p in (data.get("projects") or []):
        if not isinstance(p, dict):
            continue
        name, rfp, form = p.get("name"), p.get("rfp"), p.get("form")
        if name and rfp and form and (SAMPLES / rfp).exists() and (SAMPLES / form).exists():
            out.append({"name": name, "rfp": rfp, "form": form})
    return out


def get_project(name: str) -> Optional[dict]:
    """과제 name → {name, rfp, form}. 없으면 None."""
    for p in list_projects():
        if p["name"] == name:
            return p
    return None


# ── 정책·KB 로드 (프롬프트 조립) ───────────────────────────────────────────
def _load_skill(name: str) -> str:
    p = SKILLS / name / "SKILL.md"
    return _read(p) if p.exists() else ""


def _policy_block(agent_md: str, skills: list[str]) -> str:
    """agent 정책 + 참조 skill 들을 하나의 안정 텍스트로 (회사·RFP 무관 → 전역 캐시 대상)."""
    parts = [f"# 정책 정본 — .claude/agents/{agent_md}\n\n{_read(AGENTS / agent_md)}"]
    for s in skills:
        body = _load_skill(s)
        if body:
            parts.append(f"\n\n# 참조 skill — {s}\n\n{body}")
    return "".join(parts)


def gather_kb(company: str) -> str:
    """회사 KB 폴더 전체를 *파일 헤더와 함께* 한 텍스트로. (회사별 분리 — 그 폴더 범위만.)"""
    base = KB_COMPANY / company
    if not base.exists():
        raise FileNotFoundError(f"회사 KB 없음: {base}")
    chunks: list[str] = [
        f"# 회사 지식베이스(KB) — kb/company/{company}/",
        "아래는 제안사의 검증된 자료 전부다. 모든 수치·실적·인증은 *여기서만* 인용하고, "
        "출처는 fills 의 source 키에 KB 경로로 적는다. KB에 없는 사실은 창작 금지 → '(확인 필요)'.",
    ]
    # 텍스트로 읽히는 것만 포함 (.md/.yaml/.txt). 이미지·바이너리는 제외 (이미지는 빌더 게이트가 처리).
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".md", ".yaml", ".yml", ".txt"}:
            rel = p.relative_to(ROOT).as_posix()
            try:
                chunks.append(f"\n\n## {rel}\n\n{_read(p)}")
            except Exception:
                continue
    return "".join(chunks)


# ── LLM 호출 — Claude Agent SDK (Max 구독 인증, API 키 불필요) ────────────────
# Claude Code CLI 로그인(구독)을 사용 → 호출이 구독에서 차감(API 크레딧 0).
# subagent 처럼 단발 완성(max_turns=1)으로 쓰되, 필요 시 파일 읽기 도구 허용 가능.
def _extract_yaml(text: str) -> str:
    """모델 출력에서 YAML 본문만. ```yaml 펜스 제거 + 파싱 검증."""
    m = re.search(r"```(?:ya?ml)?\s*\n(.*?)```", text, re.S)
    body = m.group(1) if m else text
    body = body.strip()
    yaml.safe_load(body)  # 파싱 실패 시 여기서 예외 → 호출부가 잡음
    return body


async def _agent_query(system_text: str, user_text: str) -> tuple[str, dict]:
    """claude-agent-sdk 단발 호출 → (최종텍스트, usage). 구독 인증 자동.

    Windows argv 길이 한도(~32K)를 피하려고 *prompt 를 async 제너레이터(stdin 스트리밍)* 로
    넘긴다. 문자열 prompt 는 argv 로 가서 대형 입력 시 WinError 206 으로 실패함.
    system_prompt 는 SDK v0.2.91+ 에서 stdin(initialize)으로 전달되어 대형도 안전.
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

    # 이 CLI 버전은 system_prompt 를 여전히 argv 로 전달 → 대형 시 Windows argv 한도 초과.
    # 그래서 정책·KB(대형)는 *user 메시지(stdin)* 로 접어 넣고, system_prompt 는 짧게 유지.
    folded = "[시스템 지침]\n" + system_text + "\n\n[작업 요청]\n" + user_text

    async def _prompt_stream():
        yield {
            "type": "user",
            "message": {"role": "user", "content": folded},
            "parent_tool_use_id": None,
        }

    options = ClaudeAgentOptions(
        system_prompt="너는 제안서 작성 전문 AI다. 아래 [시스템 지침]을 정확히 준수하고, "
                      "요청된 YAML 본문만 출력한다.",
        model=MODEL,
        permission_mode="bypassPermissions",
        max_turns=1,                 # 단발 완성 (도구 루프 없음)
        allowed_tools=[],            # 순수 생성 — 입력은 프롬프트에 모두 주입됨
        cwd=str(ROOT),
    )
    parts: list[str] = []
    meta: dict = {}
    async for msg in query(prompt=_prompt_stream(), options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    parts.append(b.text)
        elif isinstance(msg, ResultMessage):
            if getattr(msg, "result", None):
                parts = [msg.result]
            u = getattr(msg, "usage", None) or {}
            meta = {
                "input": (u or {}).get("input_tokens", 0),
                "output": (u or {}).get("output_tokens", 0),
                "cache_read": (u or {}).get("cache_read_input_tokens", 0),
                "cache_write": (u or {}).get("cache_creation_input_tokens", 0),
                "cost_usd": getattr(msg, "total_cost_usd", None),
                "is_error": getattr(msg, "is_error", False),
                "subtype": getattr(msg, "subtype", None),
            }
    return "".join(parts), meta


def _call_llm(system_text: str, user_text: str, log: ProgressFn,
              max_tokens: int = 64000) -> tuple[str, dict]:
    """Agent SDK 단발 호출 (구독). max_tokens 는 호환용 — Claude Code가 내부 관리."""
    import asyncio
    text, meta = asyncio.run(_agent_query(system_text, user_text))
    if meta.get("is_error"):
        raise RuntimeError(f"Agent SDK 호출 실패 (subtype={meta.get('subtype')}).")
    cost = meta.get("cost_usd")
    log(f"  · tokens in={meta.get('input',0)} out={meta.get('output',0)} "
        f"cache_read={meta.get('cache_read',0)}"
        + (f" cost≈${cost:.3f}(구독차감)" if isinstance(cost, (int, float)) else ""))
    if not text.strip():
        raise RuntimeError("Agent SDK 가 빈 응답을 반환했습니다.")
    return text, meta


def _call_llm_yaml(system_text: str, user_text: str, log: ProgressFn,
                   label: str = "", max_repair: int = 2) -> tuple[str, dict]:
    """YAML 출력 LLM 호출 + 파싱 실패 시 *자가복구* 재호출 (LLM 출력 견고화).

    LLM 이 콜론(:)·괄호·특수문자가 든 값을 따옴표로 감싸지 않으면 YAML 파싱이 실패한다
    (예: `사업기간: 2026∼2027년 (타입1: 협약일∼1년 …)` — 값 안의 콜론을 nested mapping
    으로 오인). 파싱 실패 시 *오류를 피드백해 재생성* 한다. 임의 RFP/회사/양식 공통 —
    특정 값·키 하드코딩 0.
    """
    raw, usage = _call_llm(system_text, user_text, log)
    for attempt in range(max_repair + 1):
        try:
            return _extract_yaml(raw), usage
        except yaml.YAMLError as e:
            if attempt >= max_repair:
                raise RuntimeError(
                    f"{label or 'LLM'} YAML 파싱 {max_repair}회 재시도 실패: {e}")
            log(f"  ⚠ {label} YAML 파싱 실패 → 자가복구 재시도 {attempt + 1}/{max_repair}")
            repair_user = user_text + (
                f"\n\n## 직전 출력이 YAML 파싱에 실패함\n오류: {e}\n"
                "문자열 값에 콜론(:)·괄호·슬래시·특수문자가 있으면 *작은따옴표로 감싸라* "
                "(예: `키: '2026∼2027년 (타입1: 협약일)'`). 유효한 YAML 문서 하나만 — "
                "설명·머리말·코드펜스 없이 YAML 본문만 다시 출력하라."
            )
            raw, usage = _call_llm(system_text, repair_user, log)


def run_rfp_analyst(rfp_text: str, form_yaml: str, log: ProgressFn = _noop) -> tuple[str, dict]:
    """RFP 본문 + 양식 form.yaml → rfp_analysis.yaml (문자열)."""
    system = _policy_block("rfp-analyst.md", ANALYST_SKILLS)
    user = (
        "아래는 분석 대상 RFP 본문(B)과 별첨 양식의 셀 구조(C = form.yaml)다. "
        "위 정책의 스키마/원칙에 따라 rfp_analysis.yaml 을 작성하라.\n"
        "- B+C 를 cross-reference 로 읽어 B_C_매핑·본체_별지 식별까지 채운다.\n"
        "- RFP 원문에 없는 값은 추측 금지(생략 또는 '확인 필요').\n"
        "- **출력은 YAML 본문만** — 설명·머리말·코드펜스 없이 YAML 문서 하나만 출력한다.\n"
        "- 문자열 값에 콜론(:)·괄호·슬래시·특수문자가 있으면 *작은따옴표로 감싸라* "
        "(예: `사업기간: '2026∼2027년 (타입1: 협약일∼1년)'`) — YAML 파싱 안전.\n\n"
        "## RFP 본문 (B)\n\n" + rfp_text +
        "\n\n## 양식 셀 구조 (C — form.yaml)\n\n```yaml\n" + form_yaml + "\n```\n"
    )
    log("→ rfp-analyst (구독)")
    return _call_llm_yaml(system, user, log, label="rfp-analyst")


def _tbl_idx(fill_id: str) -> Optional[int]:
    """fill_target id 'T{n}_R{r}_C{c}' 에서 표 인덱스 n 추출."""
    m = re.match(r"T(\d+)_", fill_id or "")
    return int(m.group(1)) if m else None


def prep_form_for_writer(form_yaml: str, table_range: Optional[list] = None) -> str:
    """proposal-writer 용 form 가공 — ① `tables` 셀 덤프 제거 ② 본체 별지 범위로 한정.

    - proposal-writer 는 fill_targets(셀+hints) 만 진리로 쓴다(agent.md §자원 우선순위).
      hints 에 left/up/table_label/table_caption 이 이미 있어 tables 전체 덤프는 중복(~70% 토큰).
    - table_range=[a,b] 가 주어지면(rfp-analyst 가 식별한 본체 별지 표 범위) 그 범위의
      fill_targets·sections 만 남긴다. CLAUDE.md 포커스(본체 별지 단독) + 출력 토큰 절감.
      범위 식별은 rfp_analysis 산출에 위임 — 셀 id·표번호를 코드에 박지 않음(임의 양식 일반).
    """
    try:
        d = yaml.safe_load(form_yaml) or {}
    except Exception:
        return form_yaml
    if not isinstance(d, dict):
        return form_yaml
    d.pop("tables", None)
    note = ["tables 덤프 생략 — 채움 대상은 fill_targets(hints 포함)만."]
    if table_range and len(table_range) == 2:
        lo, hi = table_range
        ft = d.get("fill_targets") or []
        kept = [t for t in ft
                if (_tbl_idx(t.get("id", "")) is not None and lo <= _tbl_idx(t["id"]) <= hi)]
        if kept:
            d["fill_targets"] = kept
            d["fill_target_count"] = len(kept)
        secs = d.get("sections") or []
        if secs:
            d["sections"] = [
                s for s in secs
                if isinstance(s.get("table_idx_range"), list) and len(s["table_idx_range"]) == 2
                and not (s["table_idx_range"][1] < lo or s["table_idx_range"][0] > hi)
            ] or secs
        note.append(f"본체 별지 표범위 {table_range} 로 한정 — fill_targets {len(kept)}개 "
                    f"(부속 별지 제외).")
    d["_note"] = " ".join(note)
    return yaml.safe_dump(d, allow_unicode=True, sort_keys=False)


def run_proposal_writer(form_yaml: str, rfp_analysis: str, company: str,
                        decisions: dict, filled_ids: list[str],
                        table_range: Optional[list] = None,
                        log: ProgressFn = _noop) -> tuple[str, dict]:
    """form.yaml + rfp_analysis + KB + 결정 → fills.yaml (서술·실적·이미지 채움)."""
    form_yaml = prep_form_for_writer(form_yaml, table_range)
    # 정책(전역) + 회사 KB(회사별)를 하나의 시스템 프롬프트로.
    system = _policy_block("proposal-writer.md", WRITER_SKILLS) + "\n\n" + gather_kb(company)
    skip = ""
    if filled_ids:
        skip = ("\n\n## 이미 자동 채움된 셀 id (회사메타·재무·사업비 — 중복 금지)\n"
                "아래 id 는 결정적 빌더가 이미 채웠다. **이 id 들은 fills 에 내지 마라.**\n"
                + ", ".join(sorted(filled_ids)))
    user = (
        "아래 입력으로 빈 셀 채움 명세 fills.yaml 을 작성하라. 위 정책(proposal-writer)을 그대로 준수한다.\n"
        "- fill_targets 의 *서술·example_row·이미지* 셀을 채운다 (회사메타·재무·사업비는 제외 — 아래 결정·자동채움 참조).\n"
        "- 비즈니스 결정을 *전 섹션 일관* 반영(단독신청이면 컨소시엄 의미 셀 전부 '해당 없음', PII 처리 등).\n"
        "- KB 검증 사실만. 미확정 수치는 '(확인 필요)', PII 는 결정에 따라 'OOO'.\n"
        "- **(확인 필요) 최소화 — KB 재검색 우선**: 수치 목표·실적이 KB에 *명시*돼 있으면 "
        "(확인 필요) 대신 그 값을 쓴다 (예: KB '수출 매출 목표 10억원' → 수출 목표 셀 = 10억). "
        "추측이 필요한 것만 (확인 필요).\n"
        "- **인력 PII 헤더는 OOO**: 성명·성별·생년월일·학교 등 *개인식별* 헤더의 데이터 셀은 "
        "(확인 필요)가 아니라 'OOO' (§5-1 익명 — '값을 모름'이 아니라 '가린 것'). "
        "직위·학위·담당·참여율·경력 등 직무·역량 셀은 KB 기반으로 채운다.\n"
        "- **출력은 YAML 본문만** — 설명·코드펜스 없이 fills.yaml 문서 하나만 출력한다.\n"
        "- text 값에 콜론(:)·괄호·특수문자가 있으면 *작은따옴표로 감싸라* — YAML 파싱 안전.\n\n"
        "## 비즈니스 결정 (decisions)\n\n```yaml\n" + yaml.safe_dump(
            decisions, allow_unicode=True, sort_keys=False) + "```\n\n"
        "## RFP 분석 결과 (rfp_analysis.yaml)\n\n```yaml\n" + rfp_analysis + "\n```\n\n"
        "## 양식 셀 구조 (form.yaml — fill_targets 가 채움 대상의 유일한 진리)\n\n```yaml\n"
        + form_yaml + "\n```" + skip + "\n"
    )
    log("→ proposal-writer (구독)")
    return _call_llm_yaml(system, user, log, label="proposal-writer")


# ── fills 병합 ─────────────────────────────────────────────────────────────
def merge_fills(sources: list[Path], out_path: Path, company: str) -> Path:
    """여러 fills.yaml 을 id 중복 제거해 병합. 뒤 소스가 우선(결정적 채움이 본체보다 우선)."""
    # 병합 캐시 — fills_total 이 모든 소스보다 최신이면 재작성 생략(mtime 유지).
    # 매번 재작성하면 fills_total mtime 이 갱신돼 하류 빌드 캐시가 무효화되므로,
    # 소스 변경 없을 때 fills_total 을 그대로 둬 빌드·분할·PDF 캐시 연쇄를 보존.
    _srcs = [s for s in sources if s.exists()]
    if (out_path.exists() and out_path.stat().st_size > 0 and _srcs
            and out_path.stat().st_mtime >= max(s.stat().st_mtime for s in _srcs)):
        return out_path
    merged: dict[str, dict] = {}  # id → entry
    for src in sources:
        if not src.exists():
            continue
        data = yaml.safe_load(_read(src)) or {}
        for e in (data.get("fills") or []):
            if isinstance(e, dict) and e.get("id"):
                merged[e["id"]] = e
    doc = {"meta": {"company": company}, "fills": list(merged.values())}
    out_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out_path


def _valid_yaml(path: Path) -> bool:
    """파일이 존재하고 비어있지 않은 유효 YAML 이면 True (이어받기 판단용)."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return yaml.safe_load(_read(path)) is not None
    except Exception:
        return False


def _fill_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = yaml.safe_load(_read(path)) or {}
    return [e["id"] for e in (data.get("fills") or []) if isinstance(e, dict) and e.get("id")]


# ── 결과 묶음 ──────────────────────────────────────────────────────────────
@dataclass
class GenResult:
    outdir: Path
    form_yaml: Path
    rfp_analysis: Path
    fills_total: Path
    filled_hwpx: Path
    pdf: Optional[Path] = None
    sep_dir: Optional[Path] = None
    usage: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ── 빌드 (LLM 불필요) ──────────────────────────────────────────────────────
def _prepare_form(form_path: Path, outdir: Path, log: ProgressFn) -> tuple[Path, Path]:
    """양식을 .hwpx 로 (필요 시 변환) + form.yaml 추출. (form.hwpx, form.yaml) 반환."""
    ext = form_path.suffix.lower()
    form_hwpx = outdir / "양식.hwpx"
    if ext == ".hwpx":
        shutil.copy(form_path, form_hwpx)
    elif ext == ".hwp":
        log("양식 .hwp → .hwpx 변환 (한컴, 1회)")
        run_script([SCRIPTS / "hwp_to_hwpx.py", form_path, form_hwpx], log)
    else:
        raise RuntimeError(f"양식 포맷 미지원: {ext} (.hwp/.hwpx 만 양식 채움 모드)")
    form_yaml = outdir / "form.yaml"
    log("양식 분석 → form.yaml")
    run_script([SCRIPTS / "extract_hwpx_form.py", form_hwpx, form_yaml], log)
    return form_hwpx, form_yaml


def build_from_fills(form_hwpx: Path, fills_total: Path, form_yaml: Path,
                     outdir: Path, stem: str, submit: bool,
                     bonche_name: Optional[str], log: ProgressFn) -> tuple[Path, Optional[Path], Optional[Path]]:
    """fills_total → 채움.hwpx → 분할 → 본체 별지 PDF. (hwpx, pdf, sep_dir)."""
    filled = outdir / f"{stem}_채움.hwpx"
    # 빌드 캐시 — 입력(fills_total·form.yaml·원본 양식)이 채움.hwpx 보다 새롭지 않으면 재사용.
    # 한컴 PDF 변환(분 단위)을 살리려면 그 입력인 hwpx 가 안 바뀌어야 PDF 캐시가 hit 한다.
    # submit(제출본=검정) 은 색이 달라지므로 캐시 안 함(항상 재빌드).
    _inm = max(fills_total.stat().st_mtime, form_yaml.stat().st_mtime, form_hwpx.stat().st_mtime)
    if (not submit and filled.exists() and filled.stat().st_size > 0
            and filled.stat().st_mtime >= _inm):
        log("빌드 → 채움.hwpx — 기존 재사용 (입력 변경 없음)")
    else:
        log("빌드 → 채움.hwpx")
        args = [SCRIPTS / "fill_hwpx_form.py", form_hwpx, fills_total, filled, form_yaml]
        if submit:
            args.append("--submit")
        run_script(args, log)

    sep_dir = outdir / "별지"
    pdf = None
    try:
        _seps = list(sep_dir.glob("*.hwpx")) if sep_dir.exists() else []
        if _seps and min(s.stat().st_mtime for s in _seps) >= filled.stat().st_mtime:
            log("별지 분할 — 기존 재사용 (채움.hwpx 변경 없음)")
        else:
            log("별지 분할")
            run_script([SCRIPTS / "split_hwpx_by_section.py", filled, form_yaml, sep_dir], log)
        target = _pick_bonche(sep_dir, bonche_name)
        if target:
            pdf = outdir / "별지_본체.pdf"
            log(f"본체 별지 PDF → {target.name}")
            run_script([SCRIPTS / "hwpx_to_pdf.py", target, pdf], log)
    except Exception as e:  # 분할/본체 식별 실패 → 전체 채움본 PDF 로 폴백
        log(f"별지 분할/본체 PDF 실패 ({e}). 전체 채움본 PDF 로 폴백.")
        sep_dir = None
    if pdf is None:
        try:
            pdf = outdir / f"{stem}_채움.pdf"
            log("전체 채움본 PDF")
            run_script([SCRIPTS / "hwpx_to_pdf.py", filled, pdf], log)
        except Exception as e:
            log(f"PDF 생성 실패 ({e}) — hwpx 만 산출.")
            pdf = None
    return filled, pdf, sep_dir


def _pick_bonche(sep_dir: Path, bonche_name: Optional[str]) -> Optional[Path]:
    """분할 결과에서 본체 별지 hwpx 를 고른다. 이름 매칭 우선, 없으면 가장 큰 파일."""
    if not sep_dir or not sep_dir.exists():
        return None
    cands = sorted(sep_dir.glob("*.hwpx"))
    if not cands:
        return None
    if bonche_name:
        key = re.sub(r"[\[\]「」\s]", "", bonche_name)[:8]
        for c in cands:
            if key and key in re.sub(r"[\[\]「」\s]", "", c.stem):
                return c
    return max(cands, key=lambda p: p.stat().st_size)


# ── 전체 생성 (LLM 포함, ~15분) ────────────────────────────────────────────
def run_generate(company: str, rfp_path: Path, form_path: Path, decisions: dict,
                 submit: bool = False, log: ProgressFn = _noop) -> GenResult:
    """회사 + RFP(공고) + 양식 + 결정 → 제안서 생성 (전 과정)."""
    rfp_path, form_path = Path(rfp_path), Path(form_path)
    stem = re.sub(r"[^\w가-힣]+", "_", rfp_path.stem)[:40] or "rfp"
    # outdir 은 *날짜 무관*(과제명 기반) — 날짜 경계(자정)를 넘어도 같은 폴더라서
    # resume·캐시가 그대로 작동한다. (날짜 폴더면 자정 후 새 폴더 → 전체 재실행.)
    # webapp 생성물은 output/_gen/ 아래로 모아 수동 날짜 산출물과 분리.
    outdir = OUTPUT / "_gen" / f"{company}_{stem}"
    outdir.mkdir(parents=True, exist_ok=True)
    usage_total = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0}
    notes: list[str] = []

    # 0) 결정 기록 + *변경 감지* — 비즈니스 결정(단독/유형/사업비 등)이 직전과 다르면
    #    결정 의존 산출물(사업비·본문·병합)을 무효화해 옛 결정 재사용을 막는다.
    #    (회사메타·재무·RFP분석·양식추출은 결정 무관 → 유지.)
    dec_path = outdir / "decisions.yaml"
    new_dec = yaml.safe_dump(decisions, allow_unicode=True, sort_keys=False)
    if dec_path.exists() and dec_path.read_text(encoding="utf-8") != new_dec:
        for _f in ("fills_budget.yaml", "fills_body.yaml", "fills_total.yaml"):
            (outdir / _f).unlink(missing_ok=True)
        log("⚠ 비즈니스 결정 변경 감지 — 사업비·본문·병합 재생성 (회사·재무·RFP분석은 유지)")
    dec_path.write_text(new_dec, encoding="utf-8")

    # 이어받기(resume) — 이미 생성된 중간산출은 재사용(특히 비싼 LLM·한컴 단계).
    # 같은 (회사·RFP) 재실행은 같은 outdir 라서 실패 지점부터 이어진다 (날짜 무관).
    rfp_analysis_path = outdir / "rfp_analysis.yaml"
    fills_profile = outdir / "fills_profile.yaml"
    fills_finance = outdir / "fills_finance.yaml"
    fills_budget = outdir / "fills_budget.yaml"
    profile_yaml = KB_COMPANY / company / "profile.yaml"
    finance_yaml = KB_COMPANY / company / "finance.yaml"

    # 1) RFP 본문 추출 (표 보존)
    rfp_txt = outdir / "rfp.txt"
    if rfp_txt.exists() and rfp_txt.stat().st_size > 0:
        log("RFP 본문 추출 — 기존 재사용")
    else:
        log("RFP 본문 추출 (표 보존)")
        run_script([SCRIPTS / "extract_proposal.py", rfp_path, rfp_txt], log)
    rfp_text = _read(rfp_txt)
    if re.search(r"<표>|\[표\]|\[table\]", rfp_text):
        notes.append("⚠ RFP 추출에 표 placeholder 흔적 — 표 유실 의심. 결과 검토 권장.")

    # 2) 양식 준비 → form.yaml
    form_hwpx = outdir / "양식.hwpx"
    form_yaml_path = outdir / "form.yaml"
    if form_hwpx.exists() and form_yaml_path.exists():
        log("양식 준비 — 기존 재사용")
    else:
        form_hwpx, form_yaml_path = _prepare_form(form_path, outdir, log)
    form_yaml = _read(form_yaml_path)

    # 3) rfp-analyst (LLM) — 이미 있으면 재호출 안 함(비싼 단계)
    if _valid_yaml(rfp_analysis_path):
        log("rfp-analyst — 기존 결과 재사용 (LLM 재호출 생략)")
        rfp_analysis = _read(rfp_analysis_path)
    else:
        rfp_analysis, u = run_rfp_analyst(rfp_text, form_yaml, log)
        _acc(usage_total, u)
        rfp_analysis_path.write_text(rfp_analysis, encoding="utf-8")
    bonche_name = _bonche_name(rfp_analysis)

    # 4) 결정적 채움 — 회사메타·재무·사업비 (각각 있으면 재사용)
    if fills_profile.exists():
        log("자동채움 회사메타 — 기존 재사용")
    else:
        log("자동채움 — 회사메타(profile)")
        run_script([SCRIPTS / "fill_company_cells.py", form_yaml_path, profile_yaml, fills_profile], log)

    if fills_finance.exists():
        log("자동채움 재무 — 기존 재사용")
    elif finance_yaml.exists():
        log("자동채움 — 재무(finance)")
        run_script([SCRIPTS / "fill_finance_cells.py", form_yaml_path, finance_yaml, fills_finance], log)
    else:
        notes.append("ℹ finance.yaml 없음 — 재무 표는 채우지 않음.")

    if fills_budget.exists():
        log("자동채움 사업비 — 기존 재사용")
    else:
        _run_budget(form_yaml_path, rfp_analysis_path, fills_budget, decisions, notes, log)

    # 5) proposal-writer (LLM) — 나머지 셀 (이미 있으면 재사용)
    fills_body_path = outdir / "fills_body.yaml"
    if _valid_yaml(fills_body_path):
        log("proposal-writer — 기존 결과 재사용 (LLM 재호출 생략)")
    else:
        filled_ids = _fill_ids(fills_profile) + _fill_ids(fills_finance) + _fill_ids(fills_budget)
        table_range = _bonche_table_range(rfp_analysis)  # 본체 별지 표범위로 한정(포커스+토큰절감)
        if table_range:
            log(f"본체 별지 표범위 {table_range} 로 proposal-writer 범위 한정")
        fills_body, u = run_proposal_writer(
            form_yaml, rfp_analysis, company, decisions, filled_ids, table_range, log)
        _acc(usage_total, u)
        fills_body_path.write_text(fills_body, encoding="utf-8")

    # 6) 병합 → fills_total (결정적 채움이 본체보다 우선 = 뒤 소스)
    fills_total = merge_fills(
        [fills_body_path, fills_profile, fills_finance, fills_budget],
        outdir / "fills_total.yaml", company)

    # 7) 빌드 → 채움.hwpx → 본체 별지 PDF
    filled_hwpx, pdf, sep_dir = build_from_fills(
        form_hwpx, fills_total, form_yaml_path, outdir, stem, submit, bonche_name, log)

    cu = _count_uncertain(fills_total)
    if cu:
        notes.append(f"ℹ '(확인 필요)' {cu}건 — 제출 전 실값으로 교체 필요.")
    log(f"완료 → {outdir}")
    return GenResult(outdir, form_yaml_path, rfp_analysis_path, fills_total,
                     filled_hwpx, pdf, sep_dir, usage_total, notes)


# ── 재빌드 (LLM 불필요, ~20초) ─────────────────────────────────────────────
def run_rebuild(outdir: Path, submit: bool = False, log: ProgressFn = _noop) -> GenResult:
    """이미 생성된 폴더의 fills_total.yaml 로 빌드만 다시 (LLM 재호출 없음)."""
    outdir = Path(outdir)
    form_yaml_path = outdir / "form.yaml"
    form_hwpx = outdir / "양식.hwpx"
    fills_total = outdir / "fills_total.yaml"
    for p in (form_yaml_path, form_hwpx, fills_total):
        if not p.exists():
            raise FileNotFoundError(f"재빌드 불가 — 없음: {p}")
    rfp_analysis_path = outdir / "rfp_analysis.yaml"
    bonche_name = _bonche_name(_read(rfp_analysis_path)) if rfp_analysis_path.exists() else None
    stem = next((f.stem.replace("_채움", "") for f in outdir.glob("*_채움.hwpx")), "rfp")
    filled_hwpx, pdf, sep_dir = build_from_fills(
        form_hwpx, fills_total, form_yaml_path, outdir, stem, submit, bonche_name, log)
    log(f"재빌드 완료 → {outdir}")
    return GenResult(outdir, form_yaml_path, rfp_analysis_path, fills_total,
                     filled_hwpx, pdf, sep_dir, {}, [])


# ── 보조 ───────────────────────────────────────────────────────────────────
def _acc(total: dict, u: dict) -> None:
    for k in total:
        total[k] += (u.get(k) or 0)


def _bonche_name(rfp_analysis_yaml: str) -> Optional[str]:
    try:
        d = yaml.safe_load(rfp_analysis_yaml) or {}
        return (((d.get("사업개요") or {}).get("본체_별지") or {}) or {}).get("이름")
    except Exception:
        return None


def _bonche_table_range(rfp_analysis_yaml: str) -> Optional[list]:
    """rfp-analyst 가 식별한 본체 별지 표 인덱스 범위 [a,b]. 없으면 None(전체 사용)."""
    try:
        d = yaml.safe_load(rfp_analysis_yaml) or {}
        rng = (((d.get("사업개요") or {}).get("본체_별지") or {}) or {}).get("table_idxs_range")
        if isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, int) for x in rng):
            return rng
    except Exception:
        pass
    return None


def _run_budget(form_yaml_path: Path, rfp_analysis_path: Path, out_path: Path,
                decisions: dict, notes: list[str], log: ProgressFn) -> None:
    """사업비 자동채움 — 결정의 사업비(국고억·유형·비율)를 CLI 로 주입. 미지정 시 생략."""
    b = decisions.get("사업비") or {}
    gov_eok = b.get("국고억")
    if gov_eok in (None, ""):
        notes.append("ℹ 사업비 국고액 미지정 — 사업비 표는 채우지 않음(셀은 '확인 필요' 처리).")
        return
    args = [SCRIPTS / "fill_budget_cells.py", form_yaml_path, rfp_analysis_path, out_path,
            "--gov-eok", str(gov_eok)]
    if b.get("유형"):
        args += ["--type", str(b["유형"])]
    for key, opt in (("self_pct", "--self-pct"), ("cash_pct", "--cash-pct"),
                     ("in_kind_pct", "--in-kind-pct"), ("gov_pct", "--gov-pct")):
        if b.get(key) not in (None, ""):
            args += [opt, str(b[key])]
    log("자동채움 — 사업비(budget)")
    try:
        run_script(args, log)
    except Exception as e:
        notes.append(f"⚠ 사업비 채움 실패 ({e}) — 사업비 셀은 비어있을 수 있음.")


def _count_uncertain(fills_total: Path) -> int:
    if not fills_total.exists():
        return 0
    data = yaml.safe_load(_read(fills_total)) or {}
    n = 0
    for e in (data.get("fills") or []):
        if isinstance(e, dict):
            txt = e.get("text") or ""
            if isinstance(txt, str) and "확인 필요" in txt:
                n += 1
            for line in (e.get("paragraphs") or []):
                if isinstance(line, str) and "확인 필요" in line:
                    n += 1
    return n


def estimate_cost(usage: dict) -> float:
    """비용(USD) — Agent SDK 가 보고한 total_cost_usd 우선(구독 차감 환산), 없으면 토큰 추정.

    구독(Max) 사용 시 실제 사용자 청구는 $0 이며, 이 값은 *환산 비용*(동일 작업의 API 가격).
    """
    if usage.get("cost_usd"):
        return float(usage["cost_usd"])
    inp = usage.get("input", 0) / 1e6 * 5.0
    out = usage.get("output", 0) / 1e6 * 25.0
    cr = usage.get("cache_read", 0) / 1e6 * 0.5
    cw = usage.get("cache_write", 0) / 1e6 * 6.25
    return inp + out + cr + cw
