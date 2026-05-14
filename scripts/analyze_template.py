#!/usr/bin/env python3
"""PPT 템플릿 자동 분석 → style.yaml 초안 생성.

사용:
    python3 scripts/analyze_template.py <template.pptx> [output_style.yaml]

자동 추출:
- 슬라이드 크기
- 마스터·레이아웃 이름·placeholder 위치
- 견본 슬라이드들의 layout·텍스트·shapes 정보
- 테마 색상(theme1~), 폰트
- 견본 슬라이드의 role 자동 추정 (텍스트 키워드 기반)

수동 매핑 필요(주석으로 표시):
- 견본 슬라이드 → 슬라이드 종류(표지/목차/본문/간지/감사) 매핑
- 본문 영역 left/top/width/height
- 본문 textbox anchor 위치
"""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu
import yaml as pyyaml


def emu_to_inch(emu):
    if emu is None:
        return None
    return round(emu / 914400, 3)


def rgb_to_hex(rgb):
    if rgb is None:
        return None
    try:
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    except Exception:
        return None


def extract_theme_colors(prs):
    """슬라이드 마스터의 테마 색상 추출."""
    colors = {}
    try:
        master = prs.slide_masters[0]
        # 슬라이드 마스터에서 fill 색상 추출
        from pptx.oxml.ns import qn
        # theme XML 직접 파싱
        theme_part = None
        for rel in master.part.rels.values():
            if "theme" in rel.target_ref:
                theme_part = rel.target_part
                break
        if theme_part is None:
            return colors

        # theme XML 파싱
        from lxml import etree
        tree = etree.fromstring(theme_part.blob)
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        scheme = tree.find(".//a:clrScheme", ns)
        if scheme is None:
            return colors

        for child in scheme:
            tag = etree.QName(child.tag).localname
            srgb = child.find(".//a:srgbClr", ns)
            if srgb is not None:
                hex_val = srgb.get("val")
                if hex_val:
                    colors[tag] = f"#{hex_val.upper()}"
            else:
                sys = child.find(".//a:sysClr", ns)
                if sys is not None:
                    last = sys.get("lastClr")
                    if last:
                        colors[tag] = f"#{last.upper()}"
    except Exception as e:
        print(f"warn: 테마 색상 추출 실패: {e}", file=sys.stderr)
    return colors


def extract_theme_fonts(prs):
    """마스터 폰트 추출."""
    fonts = {}
    try:
        master = prs.slide_masters[0]
        theme_part = None
        for rel in master.part.rels.values():
            if "theme" in rel.target_ref:
                theme_part = rel.target_part
                break
        if theme_part is None:
            return fonts

        from lxml import etree
        tree = etree.fromstring(theme_part.blob)
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        font_scheme = tree.find(".//a:fontScheme", ns)
        if font_scheme is None:
            return fonts
        major = font_scheme.find(".//a:majorFont/a:latin", ns)
        minor = font_scheme.find(".//a:minorFont/a:latin", ns)
        if major is not None:
            fonts["major"] = major.get("typeface")
        if minor is not None:
            fonts["minor"] = minor.get("typeface")
        # 한글 폰트 (ea = East Asian)
        major_ea = font_scheme.find(".//a:majorFont/a:ea", ns)
        minor_ea = font_scheme.find(".//a:minorFont/a:ea", ns)
        if major_ea is not None and major_ea.get("typeface"):
            fonts["major_ea"] = major_ea.get("typeface")
        if minor_ea is not None and minor_ea.get("typeface"):
            fonts["minor_ea"] = minor_ea.get("typeface")
    except Exception as e:
        print(f"warn: 테마 폰트 추출 실패: {e}", file=sys.stderr)
    return fonts


def analyze_layouts(prs):
    """슬라이드 마스터의 레이아웃·placeholder 분석."""
    master = prs.slide_masters[0]
    layouts_info = []
    for idx, layout in enumerate(master.slide_layouts):
        placeholders = []
        for ph in layout.placeholders:
            placeholders.append({
                "idx": ph.placeholder_format.idx,
                "type": str(ph.placeholder_format.type),
                "name": ph.name,
                "left": emu_to_inch(ph.left),
                "top": emu_to_inch(ph.top),
                "width": emu_to_inch(ph.width),
                "height": emu_to_inch(ph.height),
            })
        layouts_info.append({
            "idx": idx,
            "name": layout.name,
            "placeholders": placeholders,
        })
    return layouts_info


def guess_sample_role(slide, slide_idx):
    """견본 슬라이드의 role 자동 추정 (텍스트 키워드 기반)."""
    layout_name = slide.slide_layout.name
    all_text = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            all_text.append(shape.text_frame.text.lower())
    text_blob = " ".join(all_text)

    # 키워드 기반 추정
    if "thank" in text_blob or "감사" in text_blob:
        return "감사"
    if "목차" in text_blob or "content" in text_blob or "toc" in text_blob:
        return "목차"
    if any(kw in layout_name.lower() for kw in ["table of content", "toc"]):
        return "목차"
    if slide_idx == 1 or "표지" in layout_name or "cover" in layout_name.lower() or "title" in layout_name.lower():
        return "표지_or_간지"  # 더 구분 필요
    if "간지" in layout_name or "section" in layout_name.lower() or "divider" in layout_name.lower():
        return "간지"
    if "본문" in layout_name or "content" in layout_name.lower() or "body" in layout_name.lower():
        return "본문"
    return "?"


def analyze_samples(prs):
    """견본 슬라이드들의 정보 추출."""
    samples = []
    for idx, slide in enumerate(prs.slides, start=1):
        shapes_info = []
        for shape in slide.shapes:
            info = {
                "name": shape.name,
                "is_placeholder": shape.is_placeholder,
                "left": emu_to_inch(shape.left),
                "top": emu_to_inch(shape.top),
                "width": emu_to_inch(shape.width),
                "height": emu_to_inch(shape.height),
            }
            if shape.is_placeholder:
                info["ph_idx"] = shape.placeholder_format.idx
                info["ph_type"] = str(shape.placeholder_format.type)
            if shape.has_text_frame:
                txt = shape.text_frame.text.strip()
                info["text"] = txt[:50] if txt else ""
                # 첫 run의 폰트 크기
                try:
                    if shape.text_frame.paragraphs and shape.text_frame.paragraphs[0].runs:
                        size = shape.text_frame.paragraphs[0].runs[0].font.size
                        if size is not None:
                            info["font_pt"] = size.pt
                except Exception:
                    pass
            shapes_info.append(info)
        samples.append({
            "idx": idx,
            "layout": slide.slide_layout.name,
            "role_guess": guess_sample_role(slide, idx),
            "shapes": shapes_info,
        })
    return samples


def main():
    if len(sys.argv) < 2:
        print("사용: python3 scripts/analyze_template.py <template.pptx> [output_style.yaml]")
        sys.exit(1)
    pptx_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else pptx_path.replace(".pptx", "_style_auto.yaml")

    prs = Presentation(pptx_path)

    print(f"분석 중: {pptx_path}", file=sys.stderr)

    slide_w = emu_to_inch(prs.slide_width)
    slide_h = emu_to_inch(prs.slide_height)
    layouts = analyze_layouts(prs)
    samples = analyze_samples(prs)
    theme_colors = extract_theme_colors(prs)
    theme_fonts = extract_theme_fonts(prs)

    # role_guess 기반 자동 매핑 후보 (사람 검토 필요)
    auto_role_map = {}
    for s in samples:
        role = s["role_guess"]
        if role and role != "?" and role not in auto_role_map:
            auto_role_map[role] = s["idx"]

    # style.yaml 초안 작성
    output = {
        "_generated_by": "scripts/analyze_template.py (자동 분석 초안 — 사람 검토 필요)",
        "_template_source": pptx_path,
        "template": {
            "path": pptx_path,
            "slide_size": {
                "width_in": slide_w,
                "height_in": slide_h,
            },
            "layouts_auto_detected": [
                {"idx": L["idx"], "name": L["name"]} for L in layouts
            ],
            "layouts": {
                "# 사람 매핑 필요": "각 종류 → 견본 슬라이드 1-기준 인덱스",
                "# 자동 추정": auto_role_map,
                "표지": auto_role_map.get("표지_or_간지", 1),
                "목차": auto_role_map.get("목차", 2),
                "간지": auto_role_map.get("간지", 3),
                "회사소개": "?",  # 사람이 결정
                "본문": auto_role_map.get("본문", 13),
                "결론": auto_role_map.get("본문", 13),
                "부록": auto_role_map.get("본문", 13),
                "감사": auto_role_map.get("감사", 10),
            },
            "body_area": {
                "# 추정값 — 본문 견본의 placeholder·textbox 위치 기반 사람 조정 필요": None,
                "left": 1.05,
                "top": 1.10,
                "width": round(slide_w - 2 * 1.05, 2) if slide_w else 11.20,
                "height": round(slide_h - 1.10 - 0.8, 2) if slide_h else 5.60,
            },
        },
        "colors_theme_extracted": theme_colors,
        "colors": {
            "# 사람 검토·조정": "theme에서 자동 추출. 회사 CI에 맞게 매핑.",
            "navy": theme_colors.get("dk2") or theme_colors.get("accent1") or "#1F365C",
            "light_navy": theme_colors.get("accent2") or "#4A6C9D",
            "gold": theme_colors.get("accent3") or "#C89B3C",
            "light_gold": theme_colors.get("accent4") or "#E6C47A",
            "grey": theme_colors.get("lt2") or "#707070",
            "light_grey": theme_colors.get("bg2") or "#E8E8E8",
            "dark": theme_colors.get("dk1") or "#222222",
            "white": "#FFFFFF",
        },
        "fonts_theme_extracted": theme_fonts,
        "fonts": {
            "body": theme_fonts.get("minor_ea") or theme_fonts.get("minor") or "맑은 고딕",
        },
        "cover": {
            "title_fit": [
                {"max_chars": 10, "pt": 54},
                {"max_chars": 18, "pt": 42},
                {"max_chars": 28, "pt": 32},
                {"max_chars": 40, "pt": 26},
                {"max_chars": 999, "pt": 22},
            ],
            "title_box": {"top": 3.0, "height": 2.7},
        },
        "content": {
            "messages_height_with_visuals": 1.4,
            "visuals_top_gap": 0.2,
            "body_textbox_anchor": {"left": 1.05, "top": 1.17},
        },
        "company_intro": {
            "headline_anchor": {"left": 1.06, "top": 1.10},
            "sub_anchor": {"left": 1.64, "top": 2.00},
        },
        "placeholder_idx": {
            "표지": {"title": 0, "sub1": 1, "sub2": 2},
            "목차": {"title": 0, "nums_left": 1, "nums_right": 2, "titles_left": 3, "titles_right": 4},
            "본문": {"title": 0, "chap_no": 1, "chap_name": 2},
            "간지": {"title": 0, "chap_no": 1},
            "감사": {"title": 0, "footer": 11},
        },
        "footer": {"top": round((slide_h or 7.5) - 0.6, 2)},
        "_samples_detected": samples,
        "_layouts_detected": layouts,
    }

    # YAML 출력 (한글 보존)
    Path(out_path).write_text(
        pyyaml.dump(output, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8"
    )
    print(f"저장: {out_path}", file=sys.stderr)
    print(f"\n=== 자동 매핑 추정 ===", file=sys.stderr)
    for role, idx in auto_role_map.items():
        print(f"  {role}: 견본 슬라이드 {idx}", file=sys.stderr)
    print(f"\n=== 검토 필요 ===", file=sys.stderr)
    print(f"  1. template.layouts — 견본 슬라이드 매핑 (회사소개·결론·부록 등 수동)", file=sys.stderr)
    print(f"  2. colors — 회사 CI와 맞는지 확인 (theme 자동 추출이 부정확할 수 있음)", file=sys.stderr)
    print(f"  3. body_area, body_textbox_anchor — 본문 견본 검증 후 조정", file=sys.stderr)
    print(f"  4. placeholder_idx — 본문 견본의 placeholder 인덱스 매핑 확인", file=sys.stderr)


if __name__ == "__main__":
    main()
