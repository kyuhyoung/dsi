#!/usr/bin/env python
"""KB 검색·비전 검증이 모두 실패했을 때 호출되는 *이미지 생성기* (Google Gemini/Imagen).

fill_hwpx_form 의 generation hook 이 argv 로 호출한다:
    python scripts/gen_image.py --out <경로> --prompt <설명> [--model <모델>]

설계 원칙 (image_schema.yaml / feedback_generalization):
  - 특정 사업·회사·이미지 하드코딩 없음. 프롬프트 = 셀의 설명(context) 그대로
    (+ generation.prompt_prefix 로 격식 제안서용 스타일 유도는 빌더가 처리).
  - API 키는 *env 에서만* 읽음 (GEMINI_API_KEY 또는 GOOGLE_API_KEY). 코드·커밋에 키 금지.
  - 모델은 --model 또는 GEN_IMAGE_MODEL env 로 교체 가능 (사내 접근 권한에 맞춤).
  - 생성 이미지는 호출측(빌더)에서 *비전 검증* 통과 후에만 삽입됨 (gen 빗나감 차단).

사용 전 준비 (1회):
  pip install google-genai pillow
  set GEMINI_API_KEY=<키>            # PowerShell: $env:GEMINI_API_KEY="<키>"

모델 선택 (사내 권한에 맞게, 둘 중 가용한 것):
  - Imagen 전용 이미지 모델:  imagen-3.0-generate-002  (기본값)
  - Gemini 멀티모달 이미지:   gemini-2.5-flash-image-preview  (Nano Banana)
  교체: --model <이름>  또는  set GEN_IMAGE_MODEL=<이름>

단독 테스트:
  python scripts/gen_image.py --out /tmp/t.png --prompt "위성 영상 기반 정밀농업 분석 솔루션 도식"
"""
import argparse
import os
import sys
from pathlib import Path

DEFAULT_MODEL = os.environ.get("GEN_IMAGE_MODEL", "imagen-3.0-generate-002")


def _api_key():
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(k)
        if v:
            return v
    sys.exit("ERROR: GEMINI_API_KEY(또는 GOOGLE_API_KEY) env 미설정 — 키 없이는 생성 불가")


def main():
    ap = argparse.ArgumentParser(description="Gemini/Imagen 이미지 생성 (gen hook)")
    ap.add_argument("--out", required=True, help="저장 경로 (.png)")
    ap.add_argument("--prompt", required=True, help="생성 프롬프트 (셀 설명)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="생성 모델 (imagen-*/gemini-*-image)")
    a = ap.parse_args()

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai 미설치 — `pip install google-genai` 후 재시도")

    client = genai.Client(api_key=_api_key())
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    img_bytes = None
    if "imagen" in a.model.lower():
        # Imagen 전용 이미지 모델 경로
        res = client.models.generate_images(
            model=a.model,
            prompt=a.prompt,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        gi = getattr(res, "generated_images", None) or []
        if gi:
            img_bytes = gi[0].image.image_bytes
    else:
        # Gemini 멀티모달 이미지 출력 경로 (inline_data 추출)
        res = client.models.generate_content(model=a.model, contents=a.prompt)
        for cand in (getattr(res, "candidates", None) or []):
            for part in (getattr(cand.content, "parts", None) or []):
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    img_bytes = inline.data
                    break
            if img_bytes:
                break

    if not img_bytes:
        sys.exit("ERROR: 생성 결과에 이미지 없음 (모델 접근권한·프롬프트·정책 확인)")

    out.write_bytes(img_bytes)
    print(f"generated: {out} ({len(img_bytes)} bytes, model={a.model})")


if __name__ == "__main__":
    main()
