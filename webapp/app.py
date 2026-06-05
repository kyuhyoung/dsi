# -*- coding: utf-8 -*-
"""
DSI 풀 생성 웹앱 — app.py (Streamlit)

회사 선택 + RFP 선택 + 비즈니스 결정 입력 → [생성] → 제안서 .hwpx/.pdf.
[재빌드] 는 이미 생성된 폴더의 fills_total.yaml 로 빌드만 (LLM 재호출 없음, ~20초·무료).

실행:  streamlit run webapp/app.py
사전:  $env:ANTHROPIC_API_KEY = 'sk-ant-...'   (PowerShell)
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import streamlit as st

# webapp 패키지 외부에서 직접 실행되므로 경로 보정
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402

st.set_page_config(page_title="Dabeeo Super Intelligence", page_icon="📄", layout="wide")


def _find_logo(company: str) -> "Path | None":
    """제안사 로고 — kb/company/<회사>/images/logo.* (규칙 파일명). 없으면 webapp/assets/logo.*.

    파일명 규칙 'logo' 로 한정 — 같은 폴더의 제안서 채움용 이미지를 잘못 집지 않게.
    """
    exts = (".png", ".jpg", ".jpeg", ".webp", ".svg")
    cands = [P.KB_COMPANY / company / "images"]
    cands.append(Path(__file__).resolve().parent / "assets")
    for d in cands:
        if d.exists():
            for ext in exts:
                hit = d / f"logo{ext}"
                if hit.exists():
                    return hit
    return None


def _render_header(company: str) -> None:
    """좌측 제목·설명 + 우측 상단 로고 (배경 아님 — 실제 로고 자리)."""
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        # 약자 DSI = 각 단어 첫 글자. D·S·I 를 크게·그라데이션·디스플레이 폰트로 강조.
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Audiowide&display=swap');
            .dsi-title { line-height: 1.05; margin: 0 0 .2rem 0; font-weight: 700; }
            .dsi-title .cap {
                font-family: 'Audiowide', system-ui, sans-serif;
                font-size: 5rem;
                background: linear-gradient(95deg, #2E6BFF 0%, #1B3FB0 55%, #0B1E6B 100%);
                -webkit-background-clip: text; background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 1px 0 rgba(0,0,0,0.04);
                padding-right: .02em;
            }
            .dsi-title .rest {
                font-size: 1.9rem; color: #2b2b2b; font-weight: 600;
                font-family: system-ui, 'Segoe UI', sans-serif; margin-right: .6rem;
            }
            </style>
            <div class="dsi-title">
                <span class="cap">D</span><span class="rest">abeeo</span><span class="cap">S</span><span class="rest">uper</span><span class="cap">I</span><span class="rest">ntelligence</span>
            </div>
        """, unsafe_allow_html=True)
        st.caption("RFP + 신청 정보 → 한국어 제안서 .hwpx / .pdf  ·  "
                   "양식은 건드리지 않고 빈 셀만 채움(검토용 녹색).")
    with right:
        img = _find_logo(company)
        if img is not None:
            st.image(str(img), use_container_width=True)


# ── 인증: Claude Code(구독) 사용 — API 키 불필요 ────────────────────────────
# Agent SDK 는 로그인된 claude CLI 의 구독을 사용한다. API 키가 있으면 (과금)혼선을 막기 위해 제거.
os.environ.pop("ANTHROPIC_API_KEY", None)
has_key = shutil.which("claude") is not None

companies = P.list_companies()
projects = P.list_projects()

if not companies:
    st.error("kb/company/ 아래에 profile.yaml 을 가진 회사가 없습니다.")
    st.stop()

# 제안사 = 사내 다비오 고정 (UI 선택 불필요). 엔진은 company 변수로 일반 동작.
COMPANY = "dabeeo" if "dabeeo" in companies else companies[0]
_render_header(COMPANY)  # 우측 상단 로고 (kb/company/<회사>/images/logo.*)

if not has_key:
    st.warning("claude CLI 를 찾지 못했습니다. Claude Code 가 설치·로그인되어 있어야 "
               "[생성]이 구독으로 동작합니다. (재빌드는 LLM 없이 가능).")

# ── 결과 표시 (다운로드 버튼) ───────────────────────────────────────────────
def _show_result(res: "P.GenResult") -> None:
    if res.notes:
        for n in res.notes:
            st.write(n)
    if res.usage:
        cost = P.estimate_cost(res.usage)
        st.caption(f"토큰  in={res.usage.get('input',0):,} · out={res.usage.get('output',0):,} · "
                   f"cache_read={res.usage.get('cache_read',0):,}  →  환산 약 ${cost:.2f} "
                   f"(Max 구독 차감 — 별도 청구 없음)")
    cols = st.columns(3)
    with cols[0]:
        if res.filled_hwpx and res.filled_hwpx.exists():
            st.download_button("⬇ 채움 .hwpx", res.filled_hwpx.read_bytes(),
                               file_name=res.filled_hwpx.name, key=f"dl_h_{res.filled_hwpx}")
    with cols[1]:
        if res.pdf and res.pdf.exists():
            st.download_button("⬇ 본체 .pdf", res.pdf.read_bytes(),
                               file_name=res.pdf.name, key=f"dl_p_{res.pdf}")
    with cols[2]:
        if res.fills_total and res.fills_total.exists():
            st.download_button("⬇ fills_total.yaml", res.fills_total.read_bytes(),
                               file_name="fills_total.yaml", key=f"dl_y_{res.fills_total}")
    if res.pdf and res.pdf.exists():
        st.caption(f"PDF 경로: {res.pdf}")


tab_gen, tab_rebuild = st.tabs(["① 풀 생성 (LLM, ~15분)", "② 재빌드 (LLM 없이, ~20초)"])

# ════════════════════════════════════════════════════════════════════════════
# ① 풀 생성
# ════════════════════════════════════════════════════════════════════════════
with tab_gen:
    company = COMPANY  # 사내 다비오 고정
    if not projects:
        st.error("등록된 과제가 없습니다. webapp/projects.yaml 에 과제(name·rfp·form)를 추가하세요.")
        st.stop()
    st.markdown("#### 과제")
    proj_names = [p["name"] for p in projects]
    proj_name = st.selectbox("과제 선택", proj_names, key="g_proj", label_visibility="collapsed",
                             help="과제별 RFP·양식은 내부에 정의되어 있습니다 (webapp/projects.yaml).")
    _proj = P.get_project(proj_name)

    st.markdown("##### 신청 정보 (직접 입력 항목)")
    d1, d2, d3 = st.columns(3)
    with d1:
        apply_form = st.radio("신청 형태", ["단독", "컨소시엄"], key="g_apply")
        pii = st.radio("참여인력 표기", ["OOO (익명)", "실명"], key="g_pii")
    with d2:
        app_type = st.text_input("신청유형 (RFP에 유형구분 있으면)", key="g_type",
                                 placeholder="예: 타입1 / 없으면 비움")
        product = st.text_input("제품·솔루션 공식명", key="g_product",
                                placeholder="예: Eartheye Plantation")
    with d3:
        gov_eok = st.number_input("국고 신청액(억원) — 0이면 미지정",
                                  min_value=0.0, step=1.0, value=0.0, key="g_gov")
        st.caption("아래 비율은 매칭펀드형일 때만 (미지정=RFP대로/확인필요)")
        bc1, bc2 = st.columns(2)
        with bc1:
            self_pct = st.number_input("자부담%", 0, 100, 0, key="g_self")
            cash_pct = st.number_input("현금%", 0, 100, 0, key="g_cash")
        with bc2:
            gov_pct = st.number_input("국고%", 0, 100, 0, key="g_govp")
            in_kind_pct = st.number_input("현물%", 0, 100, 0, key="g_inkind")

    submit_black = st.checkbox("제출본(검정 글자)으로 빌드 — 기본은 검토용 녹색", key="g_submit")

    def _decisions() -> dict:
        b: dict = {}
        if gov_eok and gov_eok > 0:
            b["국고억"] = float(gov_eok)
        if app_type.strip():
            b["유형"] = app_type.strip()
        for k, v in (("self_pct", self_pct), ("cash_pct", cash_pct),
                     ("gov_pct", gov_pct), ("in_kind_pct", in_kind_pct)):
            if v:
                b[k] = float(v)
        return {
            "신청형태": apply_form,
            "신청유형": app_type.strip() or "해당없음",
            "사업비": b,
            "제품명": product.strip() or "(확인 필요)",
            "PII": "실명" if pii == "실명" else "OOO",
        }

    go = st.button("🚀 제안서 생성", type="primary", disabled=not has_key, key="g_go")
    if go:
        rfp_path = P.SAMPLES / _proj["rfp"]
        form_path = P.SAMPLES / _proj["form"]
        logbox = st.empty()
        logs: list[str] = []

        def log(msg: str) -> None:
            logs.append(msg)
            logbox.code("\n".join(logs[-30:]), language="text")

        with st.status("생성 중… (RFP 분석·본문 작성이 대부분 — 약 13~20분)", expanded=True):
            try:
                res = P.run_generate(company, rfp_path, form_path, _decisions(),
                                     submit=submit_black, log=log)
            except Exception as e:
                st.error(f"생성 실패: {e}")
                st.stop()
        st.success(f"완료 → {res.outdir}")
        _show_result(res)


# ════════════════════════════════════════════════════════════════════════════
# ② 재빌드
# ════════════════════════════════════════════════════════════════════════════
with tab_rebuild:
    st.caption("이미 생성된 폴더(fills_total.yaml 포함)를 골라 빌드만 다시 — LLM 재호출 없음.")
    folders = sorted(
        (p for p in P.OUTPUT.rglob("fills_total.yaml")),
        key=lambda p: p.stat().st_mtime, reverse=True)
    if not folders:
        st.info("재빌드 가능한 폴더가 없습니다 (fills_total.yaml 포함 폴더).")
    else:
        labels = [str(f.parent.relative_to(P.OUTPUT)) for f in folders]
        pick = st.selectbox("생성된 폴더", labels, key="r_pick")
        submit_black2 = st.checkbox("제출본(검정 글자)으로", key="r_submit")
        if st.button("🔁 재빌드", key="r_go"):
            outdir = P.OUTPUT / pick
            logbox2 = st.empty()
            logs2: list[str] = []

            def log2(msg: str) -> None:
                logs2.append(msg)
                logbox2.code("\n".join(logs2[-30:]), language="text")

            with st.status("재빌드 중… (~20초)", expanded=True):
                try:
                    res = P.run_rebuild(outdir, submit=submit_black2, log=log2)
                except Exception as e:
                    st.error(f"재빌드 실패: {e}")
                    st.stop()
            st.success(f"재빌드 완료 → {res.outdir}")
            _show_result(res)
