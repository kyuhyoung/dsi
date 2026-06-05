# -*- coding: utf-8 -*-
"""라이브 1건 실측 러너 — webapp 백엔드를 CLI 로 호출(실측·검증용).

키는 환경변수 ANTHROPIC_API_KEY 또는 webapp/.env 에서 로드.
사용: python webapp/run_once.py <회사> <RFP파일명> <양식파일명>
비즈니스 결정은 기존 확정값(농식품: 단독·타입1·국고20억·OOO) 재사용 — 인자로 override 가능.
"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Agent SDK 는 Claude Code 구독 로그인을 사용 → API 키 불필요.
# ANTHROPIC_API_KEY 가 환경에 있으면 (소진된)API 과금으로 라우팅되므로 제거.
os.environ.pop("ANTHROPIC_API_KEY", None)

import pipeline as P  # noqa: E402

company = sys.argv[1] if len(sys.argv) > 1 else "dabeeo"
rfp_name = sys.argv[2] if len(sys.argv) > 2 else \
    "농식품 분야 「AI 응용제품 신속상용화 지원사업」 모집 공고.hwp"
form_name = sys.argv[3] if len(sys.argv) > 3 else \
    "[양식] 농식품 분야 「AI 응용제품 신속상용화 지원사업」.hwp"

# 기존 확정 비즈니스 결정 (output/20260602 fills 에서 확인 — 임의 생성 아님)
decisions = {
    "신청형태": "단독",
    "신청유형": "타입1",
    "사업비": {"국고억": 20.0, "유형": "타입1"},
    "제품명": "Eartheye Plantation — AI 기반 위성·드론·모바일 통합 정밀농업 솔루션",
    "PII": "OOO",
}

t0 = time.time()
log_lines = []


def log(msg: str) -> None:
    t = time.time() - t0
    line = f"[{t:6.1f}s] {msg}"
    print(line, flush=True)
    log_lines.append(line)


log(f"START  회사={company}  RFP={rfp_name}  양식={form_name}")
try:
    res = P.run_generate(company, P.SAMPLES / rfp_name, P.SAMPLES / form_name,
                         decisions, submit=False, log=log)
except Exception as e:
    log(f"FAILED: {e}")
    raise
dt = time.time() - t0
log(f"DONE in {dt:.0f}s ({dt/60:.1f}min)")
log(f"outdir = {res.outdir}")
log(f"hwpx   = {res.filled_hwpx}")
log(f"pdf    = {res.pdf}")
log(f"usage  = {res.usage}  →  ~${P.estimate_cost(res.usage):.2f}")
for n in res.notes:
    log(f"note   = {n}")
