#!/usr/bin/env python3
"""PPT 구성안 YAML → pptx 변환.

v4: 견본 복제 + 시각화 함수 통합.
- 견본 슬라이드 복제 (다비오 템플릿)
- 시각요소(시각요소 항목)를 구조화된 type으로 자동 그리기:
  flow_arrow / matrix_2x2 / bar_chart / timeline / callout_cards
- 시각화 type이 있으면 본문 영역을 핵심메시지 상단 + 시각화 하단으로 분할

견본 매핑:
  종류=표지     → 견본 Slide 1
  종류=목차     → 견본 Slide 2
  종류=간지     → 견본 Slide 3
  종류=본문     → 견본 Slide 13
  종류=결론     → 견본 Slide 13
  종류=부록     → 견본 Slide 13
  종류=회사소개 → 견본 Slide 7
  종류=감사     → 견본 Slide 10
"""
import sys
import copy
import os
import zipfile
from pathlib import Path
import yaml
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE


STYLE_PATH = "templates/dabeeo_style.yaml"

# ── 기본값 (style.yaml 미존재 시 fallback) ──
TEMPLATE_PATH = "templates/Dabeeo_presentation_Template_2022_v1.pptx"

SAMPLE_MAP_1BASED = {
    "표지":     1,
    "목차":     2,
    "간지":     3,
    "회사소개": 7,
    "본문":     13,
    "결론":     13,
    "부록":     13,
    "감사":     10,
}

NAVY = RGBColor(0x1F, 0x36, 0x5C)
LIGHT_NAVY = RGBColor(0x4A, 0x6C, 0x9D)
GOLD = RGBColor(0xC8, 0x9B, 0x3C)
LIGHT_GOLD = RGBColor(0xE6, 0xC4, 0x7A)
GREY = RGBColor(0x70, 0x70, 0x70)
LIGHT_GREY = RGBColor(0xE8, 0xE8, 0xE8)
DARK = RGBColor(0x22, 0x22, 0x22)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# 표지 제목 자동 fit 룰 (style.yaml에서 override 가능)
TITLE_FIT_RULES = [
    {"max_chars": 10, "pt": 54},
    {"max_chars": 18, "pt": 42},
    {"max_chars": 28, "pt": 32},
    {"max_chars": 40, "pt": 26},
    {"max_chars": 999, "pt": 22},
]

# 본문 영역 (style.yaml에서 override 가능)
BODY_AREA = {"left": 1.05, "top": 1.10, "width": 11.20, "height": 5.60}
COVER_TITLE_BOX = {"top": 3.0, "height": 2.7}
CONTENT_LAYOUT = {"messages_height_with_visuals": 1.4, "visuals_top_gap": 0.2}
BODY_TEXTBOX_ANCHOR = {"left": 1.05, "top": 1.17}
COMPANY_INTRO_ANCHORS = {
    "headline": {"left": 1.06, "top": 1.10},
    "sub": {"left": 1.64, "top": 2.00},
}
PLACEHOLDER_IDX = {
    "표지": {"title": 0, "sub1": 1, "sub2": 2},
    "목차": {"title": 0, "nums_left": 1, "nums_right": 2, "titles_left": 3, "titles_right": 4},
    "본문": {"title": 0, "chap_no": 1, "chap_name": 2},
    "간지": {"title": 0, "chap_no": 1},
    "감사": {"title": 0, "footer": 11},
}
FONT_BODY = "맑은 고딕"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def load_style(style_path=STYLE_PATH):
    """style.yaml 로드하여 모듈 레벨 상수 갱신.
    파일 없거나 키 누락 시 기본값 유지 (fallback)."""
    global TEMPLATE_PATH, SAMPLE_MAP_1BASED
    global NAVY, LIGHT_NAVY, GOLD, LIGHT_GOLD, GREY, LIGHT_GREY, DARK, WHITE
    global TITLE_FIT_RULES, BODY_AREA, COVER_TITLE_BOX, CONTENT_LAYOUT, FONT_BODY

    p = Path(style_path)
    if not p.exists():
        print(f"style.yaml 없음 (기본값 사용): {style_path}", file=sys.stderr)
        return

    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    template = data.get("template", {})
    if "path" in template:
        TEMPLATE_PATH = template["path"]
    layouts = template.get("layouts")
    if isinstance(layouts, dict):
        SAMPLE_MAP_1BASED = dict(layouts)
    body = template.get("body_area")
    if isinstance(body, dict):
        BODY_AREA.update(body)

    colors = data.get("colors", {}) or {}
    if "navy" in colors: NAVY = _hex_to_rgb(colors["navy"])
    if "light_navy" in colors: LIGHT_NAVY = _hex_to_rgb(colors["light_navy"])
    if "gold" in colors: GOLD = _hex_to_rgb(colors["gold"])
    if "light_gold" in colors: LIGHT_GOLD = _hex_to_rgb(colors["light_gold"])
    if "grey" in colors: GREY = _hex_to_rgb(colors["grey"])
    if "light_grey" in colors: LIGHT_GREY = _hex_to_rgb(colors["light_grey"])
    if "dark" in colors: DARK = _hex_to_rgb(colors["dark"])
    if "white" in colors: WHITE = _hex_to_rgb(colors["white"])

    fonts = data.get("fonts", {}) or {}
    if "body" in fonts:
        FONT_BODY = fonts["body"]

    cover = data.get("cover", {}) or {}
    if isinstance(cover.get("title_fit"), list):
        TITLE_FIT_RULES = cover["title_fit"]
    if isinstance(cover.get("title_box"), dict):
        COVER_TITLE_BOX.update(cover["title_box"])

    content_cfg = data.get("content", {}) or {}
    if isinstance(content_cfg, dict):
        # body_textbox_anchor는 별도 dict로
        if "body_textbox_anchor" in content_cfg:
            BODY_TEXTBOX_ANCHOR.update(content_cfg["body_textbox_anchor"])
        # 나머지 키만 CONTENT_LAYOUT에
        for k, v in content_cfg.items():
            if k != "body_textbox_anchor":
                CONTENT_LAYOUT[k] = v

    ci = data.get("company_intro", {}) or {}
    if isinstance(ci, dict):
        if "headline_anchor" in ci:
            COMPANY_INTRO_ANCHORS["headline"].update(ci["headline_anchor"])
        if "sub_anchor" in ci:
            COMPANY_INTRO_ANCHORS["sub"].update(ci["sub_anchor"])

    ph_idx = data.get("placeholder_idx", {}) or {}
    if isinstance(ph_idx, dict):
        for kind, mapping in ph_idx.items():
            if kind in PLACEHOLDER_IDX and isinstance(mapping, dict):
                PLACEHOLDER_IDX[kind].update(mapping)
            elif isinstance(mapping, dict):
                PLACEHOLDER_IDX[kind] = dict(mapping)

    print(f"style 로드됨: {style_path}", file=sys.stderr)


# ─────────────────────────────────────────
# 슬라이드 복제·유틸
# ─────────────────────────────────────────

def duplicate_slide(prs, src_slide):
    blank = src_slide.slide_layout
    dest = prs.slides.add_slide(blank)
    for shp in list(dest.shapes):
        sp = shp._element
        sp.getparent().remove(sp)
    for shp in src_slide.shapes:
        el = shp._element
        new_el = copy.deepcopy(el)
        dest.shapes._spTree.append(new_el)
    return dest


def set_run_text(shape, new_text, keep_font=True):
    if not shape.has_text_frame:
        return
    tf = shape.text_frame
    saved_font = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        r0 = tf.paragraphs[0].runs[0]
        saved_font = {
            "name": r0.font.name,
            "size": r0.font.size,
            "bold": r0.font.bold,
            "italic": r0.font.italic,
        }
        try:
            saved_font["color"] = r0.font.color.rgb
        except Exception:
            saved_font["color"] = None
    tf.text = ""
    lines = str(new_text).split("\n") if new_text is not None else [""]
    first = True
    for line in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        r = p.add_run()
        r.text = line
        if keep_font and saved_font:
            if saved_font["name"]:
                r.font.name = saved_font["name"]
            if saved_font["size"]:
                r.font.size = saved_font["size"]
            if saved_font["bold"] is not None:
                r.font.bold = saved_font["bold"]
            if saved_font["italic"] is not None:
                r.font.italic = saved_font["italic"]
            if saved_font.get("color"):
                try:
                    r.font.color.rgb = saved_font["color"]
                except Exception:
                    pass


def set_run_font(run, name="맑은 고딕", size=14, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def find_shape_by_text(slide, search):
    for shape in slide.shapes:
        if shape.has_text_frame:
            txt = shape.text_frame.text.strip()
            if txt.startswith(search) or search in txt:
                return shape
    return None


def find_shape_by_pos(slide, left_inch, top_inch, tol=0.3):
    target_l = Inches(left_inch)
    target_t = Inches(top_inch)
    for shape in slide.shapes:
        if shape.left is None or shape.top is None:
            continue
        dl = abs(shape.left - target_l) / 914400
        dt = abs(shape.top - target_t) / 914400
        if dl < tol and dt < tol:
            return shape
    return None


def find_shape_by_placeholder_idx(slide, idx):
    for shape in slide.shapes:
        if shape.is_placeholder and shape.placeholder_format.idx == idx:
            return shape
    return None


# ─────────────────────────────────────────
# 시각화 함수들 (NEW)
# ─────────────────────────────────────────

def draw_flow_arrow(slide, items, left, top, width, height):
    """N개 단계를 가로 화살표 흐름으로 그림."""
    n = len(items)
    if n == 0:
        return
    gap = 0.2
    total_gap = gap * (n - 1)
    box_w = (width - total_gap) / n
    box_h = min(height * 0.6, 1.3)
    box_top = top + (height - box_h) / 2

    for i, item in enumerate(items):
        x = left + i * (box_w + gap)
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(box_top), Inches(box_w), Inches(box_h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = NAVY
        shape.line.fill.background()
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(item)
        set_run_font(r, size=14, bold=True, color=WHITE)

        if i < n - 1:
            arr_x = x + box_w + 0.02
            arr_y = box_top + box_h / 2 - 0.12
            arr_w = gap - 0.04
            arr = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW,
                Inches(arr_x), Inches(arr_y),
                Inches(arr_w), Inches(0.24)
            )
            arr.fill.solid()
            arr.fill.fore_color.rgb = GOLD
            arr.line.fill.background()


def draw_matrix_2x2(slide, x_axis, y_axis, quadrants, left, top, width, height):
    """2×2 매트릭스."""
    label_pad_left = 0.4
    label_pad_bottom = 0.35
    mx_left = left + label_pad_left
    mx_top = top + 0.05
    mx_w = width - label_pad_left - 0.05
    mx_h = height - label_pad_bottom - 0.1

    cell_w = mx_w / 2
    cell_h = mx_h / 2

    if isinstance(quadrants, dict):
        cells = [
            quadrants.get("Q2", quadrants.get("좌상", "")),
            quadrants.get("Q1", quadrants.get("우상", "")),
            quadrants.get("Q3", quadrants.get("좌하", "")),
            quadrants.get("Q4", quadrants.get("우하", "")),
        ]
    else:
        cells = list(quadrants) + [""] * (4 - len(quadrants))

    colors = [LIGHT_NAVY, NAVY, GREY, GOLD]
    positions = [
        (mx_left, mx_top),
        (mx_left + cell_w, mx_top),
        (mx_left, mx_top + cell_h),
        (mx_left + cell_w, mx_top + cell_h),
    ]

    for (x, y), label, color in zip(positions, cells, colors):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(x), Inches(y), Inches(cell_w), Inches(cell_h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.color.rgb = WHITE
        shape.line.width = Pt(2)
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(label)
        set_run_font(r, size=15, bold=True, color=WHITE)

    # x축 라벨 (하단 중앙)
    x_lbl = slide.shapes.add_textbox(
        Inches(mx_left), Inches(mx_top + mx_h + 0.05),
        Inches(mx_w), Inches(label_pad_bottom)
    )
    tf = x_lbl.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"→  {x_axis}"
    set_run_font(r, size=12, bold=True, color=DARK)

    # y축 라벨 (좌측 상단)
    y_lbl = slide.shapes.add_textbox(
        Inches(left), Inches(mx_top),
        Inches(label_pad_left - 0.05), Inches(0.4)
    )
    tf = y_lbl.text_frame
    r = tf.paragraphs[0].add_run()
    r.text = f"↑\n{y_axis}"
    set_run_font(r, size=11, bold=True, color=DARK)


def draw_bar_chart(slide, title, categories, series, left, top, width, height):
    """막대 차트."""
    if not categories or not series:
        return
    chart_data = CategoryChartData()
    chart_data.categories = list(categories)
    for name, values in series.items():
        chart_data.add_series(str(name), list(values))
    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(left), Inches(top),
        Inches(width), Inches(height),
        chart_data
    )
    chart = chart_shape.chart
    if title:
        chart.has_title = True
        chart.chart_title.text_frame.text = str(title)
        for run in chart.chart_title.text_frame.paragraphs[0].runs:
            set_run_font(run, size=14, bold=True, color=NAVY)
    chart.has_legend = len(series) > 1


def draw_timeline(slide, items, left, top, width, height):
    """가로 타임라인 (점·라인·라벨)."""
    n = len(items)
    if n == 0:
        return
    line_y = top + height * 0.5
    pad_x = 0.4

    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left + pad_x), Inches(line_y - 0.02),
        Inches(width - 2 * pad_x), Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = NAVY
    line.line.fill.background()

    if n == 1:
        step = 0
        start_x = left + width / 2
    else:
        step = (width - 2 * pad_x) / (n - 1)
        start_x = left + pad_x

    for i, item in enumerate(items):
        x = start_x + i * step
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(x - 0.18), Inches(line_y - 0.18),
            Inches(0.36), Inches(0.36)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = GOLD
        dot.line.color.rgb = NAVY
        dot.line.width = Pt(2)

        if isinstance(item, dict):
            label = item.get("label", "")
            content = item.get("content", "")
        else:
            label = str(item)
            content = ""

        # 라벨 배치 (홀수=위, 짝수=아래)
        if i % 2 == 0:
            lbl_top = top
            lbl_h = (line_y - top) - 0.25
        else:
            lbl_top = line_y + 0.25
            lbl_h = (top + height - line_y) - 0.25

        lbl_w = min(step * 0.95 if step else 2.0, 2.0)
        lbl_box = slide.shapes.add_textbox(
            Inches(x - lbl_w / 2), Inches(lbl_top),
            Inches(lbl_w), Inches(max(lbl_h, 0.5))
        )
        tf = lbl_box.text_frame
        tf.word_wrap = True
        if i % 2 == 0:
            tf.vertical_anchor = MSO_ANCHOR.BOTTOM
        else:
            tf.vertical_anchor = MSO_ANCHOR.TOP

        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        set_run_font(r, size=12, bold=True, color=NAVY)
        if content:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            r2.text = content
            set_run_font(r2, size=10, color=GREY)


def draw_image(slide, path, left, top, width, height, fit="contain"):
    """이미지 삽입.
    fit=contain: 비율 유지하며 영역 안에 맞춤 (기본)
    fit=cover:   영역을 가득 채움 (잘릴 수 있음)
    fit=exact:   영역에 강제로 채움 (왜곡 가능)"""
    import os
    if not os.path.exists(path):
        # 이미지 없으면 placeholder 박스 + 경고 텍스트
        box = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(left), Inches(top), Inches(width), Inches(height)
        )
        box.fill.solid()
        box.fill.fore_color.rgb = LIGHT_GREY
        box.line.color.rgb = GREY
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = f"[이미지 없음]\n{path}"
        set_run_font(r, size=10, color=GREY)
        return None

    try:
        from PIL import Image as PILImage
        img = PILImage.open(path)
        iw, ih = img.size
        aspect = iw / ih
    except Exception:
        aspect = 16 / 9  # fallback

    target_aspect = width / height if height > 0 else 1.0

    if fit == "contain":
        if aspect > target_aspect:
            w = width
            h = width / aspect
            l = left
            t = top + (height - h) / 2
        else:
            h = height
            w = height * aspect
            l = left + (width - w) / 2
            t = top
    elif fit == "cover":
        if aspect > target_aspect:
            h = height
            w = height * aspect
            l = left - (w - width) / 2
            t = top
        else:
            w = width
            h = width / aspect
            l = left
            t = top - (h - height) / 2
    else:  # exact
        l, t, w, h = left, top, width, height

    slide.shapes.add_picture(
        path, Inches(l), Inches(t), Inches(w), Inches(h)
    )


def draw_mermaid(slide, mermaid_code, left, top, width, height, theme="default", background="white"):
    """Mermaid 텍스트를 PNG로 변환해서 슬라이드에 삽입.
    캐시: .cache/mermaid/<hash>.png로 같은 코드는 재생성 안 함."""
    import subprocess
    import hashlib

    if not mermaid_code or not mermaid_code.strip():
        return

    cache_key = hashlib.md5(
        (mermaid_code + theme + background).encode("utf-8")
    ).hexdigest()[:12]
    cache_dir = Path(".cache/mermaid")
    cache_dir.mkdir(parents=True, exist_ok=True)
    png_path = cache_dir / f"{cache_key}.png"

    if not png_path.exists():
        mmd_path = cache_dir / f"{cache_key}.mmd"
        mmd_path.write_text(mermaid_code, encoding="utf-8")

        mmdc_bin = Path("node_modules/.bin/mmdc")
        if not mmdc_bin.exists():
            # mmdc 없으면 placeholder
            box = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(left), Inches(top), Inches(width), Inches(height)
            )
            box.fill.solid()
            box.fill.fore_color.rgb = LIGHT_GREY
            tf = box.text_frame
            tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = "[Mermaid CLI 미설치: node_modules/.bin/mmdc 없음]"
            set_run_font(r, size=11, color=GREY)
            return

        try:
            # 고해상도 PNG: -s 3 (스케일 3배), -w/-H로 베이스 픽셀 지정
            result = subprocess.run(
                [str(mmdc_bin), "-i", str(mmd_path), "-o", str(png_path),
                 "-t", theme, "-b", background,
                 "-w", "1600", "-H", "900", "-s", "2", "--quiet"],
                capture_output=True, text=True, timeout=90
            )
            if result.returncode != 0:
                print(f"mmdc 오류: {result.stderr[:300]}", file=sys.stderr)
                return
        except Exception as e:
            print(f"mmdc 실행 실패: {e}", file=sys.stderr)
            return

    if png_path.exists():
        draw_image(slide, str(png_path), left, top, width, height, fit="contain")


def draw_callout_cards(slide, items, left, top, width, height):
    """N개 강조 카드 가로 배치.
    카드는 콘텐츠 분량에 맞춰 컴팩트한 높이로, 영역 안 세로 중앙 정렬."""
    n = len(items)
    if n == 0:
        return
    gap = 0.25
    total_gap = gap * (n - 1)
    card_w = (width - total_gap) / n

    # 카드는 시각요소 영역 전체를 차지. 콘텐츠는 카드 안 세로 중앙으로 정렬.
    target_card_h = height
    card_top = top

    for i, item in enumerate(items):
        x = left + i * (card_w + gap)
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(card_top), Inches(card_w), Inches(target_card_h)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = NAVY
        card.line.width = Pt(1.5)

        # 상단 강조 라인 (카드 둥근 모서리 안쪽에 끼움)
        bar_h_margin = 0.12
        bar_v_margin = 0.20
        bar_thickness = 0.06
        bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x + bar_v_margin),
            Inches(card_top + bar_h_margin),
            Inches(card_w - 2 * bar_v_margin),
            Inches(bar_thickness)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = GOLD
        bar.line.fill.background()

        if isinstance(item, dict):
            title = item.get("title", "")
            body = item.get("body", "")
        else:
            title = str(item)
            body = ""

        # 콘텐츠를 카드 정중앙에 명시 위치로 배치 (vertical_anchor는 LibreOffice 변환에서 불안정)
        estimated_content_h = 1.2  # 번호(24pt) + 제목(15pt) + 본문(11pt) + 단락 간격
        content_top = card_top + (target_card_h - estimated_content_h) / 2
        text_box = slide.shapes.add_textbox(
            Inches(x + 0.25), Inches(content_top),
            Inches(card_w - 0.5), Inches(estimated_content_h + 0.3)
        )
        tf = text_box.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = f"0{i + 1}"
        set_run_font(r, size=24, bold=True, color=GOLD)
        p.space_after = Pt(6)

        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = title
        set_run_font(r2, size=15, bold=True, color=NAVY)
        p2.space_after = Pt(6)

        if body:
            p3 = tf.add_paragraph()
            r3 = p3.add_run()
            r3.text = body
            set_run_font(r3, size=11, color=DARK)


VISUAL_DISPATCH = {
    "flow_arrow": lambda s, v, l, t, w, h: draw_flow_arrow(s, v.get("items", []), l, t, w, h),
    "matrix_2x2": lambda s, v, l, t, w, h: draw_matrix_2x2(
        s, v.get("x_axis", ""), v.get("y_axis", ""), v.get("quadrants", {}), l, t, w, h),
    "bar_chart": lambda s, v, l, t, w, h: draw_bar_chart(
        s, v.get("title", ""), v.get("categories", []), v.get("series", {}), l, t, w, h),
    "timeline": lambda s, v, l, t, w, h: draw_timeline(s, v.get("items", []), l, t, w, h),
    "callout_cards": lambda s, v, l, t, w, h: draw_callout_cards(s, v.get("items", []), l, t, w, h),
    "image": lambda s, v, l, t, w, h: draw_image(
        s, v.get("path", ""), l, t, w, h, fit=v.get("fit", "contain")),
    "mermaid": lambda s, v, l, t, w, h: draw_mermaid(
        s, v.get("code", ""), l, t, w, h,
        theme=v.get("theme", "default"),
        background=v.get("background", "white")),
}


def render_visuals(slide, visuals, left, top, width, height):
    """구조화 시각요소 리스트를 세로 분할로 그림."""
    structured = [v for v in visuals if isinstance(v, dict) and "type" in v]
    if not structured:
        return False
    n = len(structured)
    gap = 0.15
    each_h = (height - gap * (n - 1)) / n
    for i, v in enumerate(structured):
        v_top = top + i * (each_h + gap)
        vtype = v.get("type")
        fn = VISUAL_DISPATCH.get(vtype)
        if fn:
            fn(slide, v, left, v_top, width, each_h)
    return True


def draw_messages_box(slide, messages, contents_dict, left, top, width, height):
    """핵심메시지·내용을 textbox로 그림 (시각요소가 있을 때 상단 영역)."""
    if not messages and not contents_dict:
        return None
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for m in messages:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        r = p.add_run()
        r.text = f"▶  {m}"
        set_run_font(r, size=18, bold=True, color=NAVY)
        p.space_after = Pt(12)

    if contents_dict and isinstance(contents_dict, dict):
        for k, v in contents_dict.items():
            p = tf.add_paragraph() if not first else tf.paragraphs[0]
            first = False
            if isinstance(v, list):
                r = p.add_run()
                r.text = f"■ {k}:"
                set_run_font(r, size=14, bold=True, color=DARK)
                p.space_after = Pt(6)
                for sub in v:
                    sp = tf.add_paragraph()
                    sr = sp.add_run()
                    sr.text = f"    · {sub}"
                    set_run_font(sr, size=12, color=GREY)
                    sp.space_after = Pt(4)
            else:
                r = p.add_run()
                r.text = f"■ {k}: {v}"
                set_run_font(r, size=14, color=DARK)
                p.space_after = Pt(8)
    return box


# ─────────────────────────────────────────
# fill 함수들
# ─────────────────────────────────────────

def fit_title_size(text):
    """표지 제목 길이 기반 폰트 크기 (style.yaml의 cover.title_fit 룰 사용)."""
    n = len(text.replace(' ', '').replace('\n', ''))
    for rule in TITLE_FIT_RULES:
        if n <= rule["max_chars"]:
            return rule["pt"]
    return TITLE_FIT_RULES[-1]["pt"]


def fill_cover(slide, sd):
    contents = sd.get("내용", {})
    사업명 = contents.get("사업명", sd.get("제목", ""))
    발주처 = contents.get("발주처", "")
    제안사 = contents.get("제안사", "")
    제출일 = contents.get("제출일", "")

    P = PLACEHOLDER_IDX["표지"]
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        # 견본 폰트 보존 (색·굵기·이름)
        set_run_text(title, 사업명, keep_font=True)
        # 크기만 자동 조정 (텍스트 길이 따라)
        size = fit_title_size(사업명)
        for p in title.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(size)
        # 박스 높이 안전 확보 (부제 영역 침범 방지) — style.yaml에서 로드
        title.top = Inches(COVER_TITLE_BOX["top"])
        title.height = Inches(COVER_TITLE_BOX["height"])

    sub1 = find_shape_by_placeholder_idx(slide, P["sub1"])
    if sub1:
        s1_parts = [p for p in [발주처, 제안사] if p]
        set_run_text(sub1, " / ".join(s1_parts))
    sub2 = find_shape_by_placeholder_idx(slide, P["sub2"])
    if sub2:
        set_run_text(sub2, 제출일)


def fill_toc(slide, sd):
    contents = sd.get("내용", {})
    sections = contents.get("섹션", [])
    P = PLACEHOLDER_IDX["목차"]
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        set_run_text(title, sd.get("제목", "목차"))
    if not sections:
        return
    n = len(sections)
    half = (n + 1) // 2
    left_items = sections[:half]
    right_items = sections[half:]

    left_nums = "\n".join(f"0{i + 1}" for i, _ in enumerate(left_items))
    right_nums = "\n".join(f"0{i + 1 + half}" for i, _ in enumerate(right_items))

    s = find_shape_by_placeholder_idx(slide, P["nums_left"])
    if s:
        set_run_text(s, left_nums)
    s = find_shape_by_placeholder_idx(slide, P["nums_right"])
    if s:
        set_run_text(s, right_nums)

    left_titles = "\n".join(str(x) for x in left_items)
    right_titles = "\n".join(str(x) for x in right_items)
    s = find_shape_by_placeholder_idx(slide, P["titles_left"])
    if s:
        set_run_text(s, left_titles)
    s = find_shape_by_placeholder_idx(slide, P["titles_right"])
    if s:
        set_run_text(s, right_titles)


def fill_section_divider(slide, sd):
    P = PLACEHOLDER_IDX["간지"]
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        set_run_text(title, sd.get("제목", ""))
    num = find_shape_by_placeholder_idx(slide, P["chap_no"])
    if num:
        sn = sd.get("번호", "")
        set_run_text(num, f"0{sn}" if str(sn).isdigit() and len(str(sn)) == 1 else str(sn))


def fill_content(slide, sd):
    """본문: 상단 제목/챕터, 하단 본문(메시지/시각요소).

    시각요소에 구조화 type이 있으면:
      메시지(상단) + 시각요소(하단) 분할
    없으면:
      기존 방식 (모든 텍스트 + 시각요소 텍스트 안내)
    """
    P = PLACEHOLDER_IDX["본문"]
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        set_run_text(title, sd.get("제목", ""))

    chap_no = find_shape_by_placeholder_idx(slide, P["chap_no"])
    if chap_no:
        n = sd.get("번호", "")
        n_str = f"{int(n):02d}" if str(n).isdigit() else str(n)
        set_run_text(chap_no, n_str)
        # 견본 박스(0.42 inch)는 "01" 정도만 들어가서 "03" 등이 줄바꿈됨 → 넓혀줌
        try:
            chap_no.text_frame.word_wrap = False
            chap_no.left = Inches(12.20)
            chap_no.width = Inches(0.65)
        except Exception:
            pass

    chap_name = find_shape_by_placeholder_idx(slide, P["chap_name"])
    if chap_name:
        kind_to_name = {"본문": "본문", "결론": "결론", "부록": "부록", "회사소개": "회사소개"}
        kind = sd.get("종류", "본문")
        set_run_text(chap_name, kind_to_name.get(kind, "본문"))
        try:
            chap_name.text_frame.word_wrap = False
        except Exception:
            pass

    # 견본의 더미 본문 textbox 식별 (style.yaml의 anchor 사용)
    body_shape = find_shape_by_pos(
        slide, BODY_TEXTBOX_ANCHOR["left"], BODY_TEXTBOX_ANCHOR["top"], tol=0.5
    )
    if body_shape is None:
        body_shape = find_shape_by_text(slide, "텍스트 서술형 내용")

    # 시각요소 구조화 검출
    visuals = sd.get("시각요소", [])
    structured_visuals = [v for v in visuals if isinstance(v, dict) and "type" in v]
    messages = sd.get("핵심메시지", [])
    contents_dict = sd.get("내용", {}) if isinstance(sd.get("내용"), dict) else {}

    # 본문 영역 (style.yaml에서 로드)
    body_left = BODY_AREA["left"]
    body_top = BODY_AREA["top"]
    body_width = BODY_AREA["width"]
    body_height = BODY_AREA["height"]

    # ─── 먼저 견본의 더미 라벨·빈 박스 정리 (시각요소 그리기 전에!) ───
    dummy_keywords = ["본문 폰트 컬러", "1단 타이틀", "글머리", "여기에 컨텐츠"]
    keep_ids = {id(s) for s in (body_shape, title, chap_no, chap_name) if s is not None}
    for shape in list(slide.shapes):
        if id(shape) in keep_ids:
            continue
        if shape.is_placeholder:
            continue
        if shape.has_text_frame:
            txt = shape.text_frame.text.strip()
            if any(kw in txt for kw in dummy_keywords):
                sp = shape._element
                sp.getparent().remove(sp)
                continue
            if not txt:
                sp = shape._element
                sp.getparent().remove(sp)
                continue
        else:
            if shape.width and shape.height:
                w_in = shape.width / 914400
                h_in = shape.height / 914400
                if w_in > 0.5 and h_in > 0.5:
                    sp = shape._element
                    sp.getparent().remove(sp)
                    continue

    # ─── 그 후에 시각요소·메시지 그리기 (정리된 깨끗한 캔버스 위에) ───
    if structured_visuals:
        # 분할 모드: 메시지(상단) + 시각요소(하단)
        if body_shape:
            set_run_text(body_shape, "")
        msg_h = 1.4 if (messages or contents_dict) else 0.0
        if msg_h > 0:
            draw_messages_box(slide, messages, contents_dict,
                              body_left, body_top, body_width, msg_h)
        viz_top = body_top + msg_h + (0.2 if msg_h > 0 else 0)
        viz_h = body_height - msg_h - (0.2 if msg_h > 0 else 0)
        render_visuals(slide, structured_visuals,
                       body_left, viz_top, body_width, viz_h)
    else:
        # 텍스트 라인 모음
        lines = []
        for m in messages:
            lines.append(f"▶  {m}")
        if contents_dict:
            if lines:
                lines.append("")
            for k, v in contents_dict.items():
                if isinstance(v, list):
                    lines.append(f"■ {k}:")
                    for sub in v:
                        lines.append(f"    · {sub}")
                else:
                    lines.append(f"■ {k}: {v}")
        if visuals:
            if lines:
                lines.append("")
            lines.append("[시각요소]")
            for v in visuals:
                lines.append(f"  · {v}")

        # 라인 수 기반 폰트 크기 자동 (18pt 기본, 많을 때만 줄임)
        n_lines = max(len(lines), 1)
        if n_lines <= 8:
            msg_font = 18
        elif n_lines <= 14:
            msg_font = 14
        else:
            msg_font = 11

        if body_shape:
            # 상단 배치 (세로 중앙 아닌, 본문 영역 위에서 시작)
            body_shape.left = Inches(body_left)
            body_shape.top = Inches(body_top)
            body_shape.width = Inches(body_width)
            body_shape.height = Inches(body_height)
            set_run_text(body_shape, "\n".join(lines))
            # 폰트 크기·굵기·줄 간격 override (색은 견본 보존)
            for p in body_shape.text_frame.paragraphs:
                p.space_after = Pt(12)
                for r in p.runs:
                    r.font.size = Pt(msg_font)
                    r.font.bold = True


def fill_company_intro(slide, sd):
    P = PLACEHOLDER_IDX["본문"]  # 회사소개도 본문 layout 사용
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        set_run_text(title, sd.get("제목", ""))
    chap_no = find_shape_by_placeholder_idx(slide, P["chap_no"])
    if chap_no:
        n = sd.get("번호", "")
        set_run_text(chap_no, f"{int(n):02d}" if str(n).isdigit() else str(n))
    chap_name = find_shape_by_placeholder_idx(slide, P["chap_name"])
    if chap_name:
        set_run_text(chap_name, "회사소개")
    ha = COMPANY_INTRO_ANCHORS["headline"]
    headline = find_shape_by_pos(slide, ha["left"], ha["top"], tol=0.4)
    if headline:
        msgs = sd.get("핵심메시지", [])
        if msgs:
            set_run_text(headline, msgs[0])
    sa = COMPANY_INTRO_ANCHORS["sub"]
    sub = find_shape_by_pos(slide, sa["left"], sa["top"], tol=0.4)
    if sub:
        msgs = sd.get("핵심메시지", [])
        sub_lines = msgs[1:] if len(msgs) > 1 else []
        contents = sd.get("내용", {})
        if isinstance(contents, dict):
            for k, v in contents.items():
                if isinstance(v, list):
                    sub_lines.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    sub_lines.append(f"{k}: {v}")
        set_run_text(sub, "\n".join(sub_lines))
    for shape in list(slide.shapes):
        if shape.has_text_frame:
            t = shape.text_frame.text.strip()
            if "dabeeo, Inc" in t:
                set_run_text(shape, "")


def fill_thanks(slide, sd):
    P = PLACEHOLDER_IDX["감사"]
    title = find_shape_by_placeholder_idx(slide, P["title"])
    if title:
        msg = sd.get("내용", {}).get("메시지", sd.get("제목", "감사합니다."))
        set_run_text(title, msg)


def add_notes(slide, notes_text):
    if not notes_text:
        return
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = notes_text.strip()


# ─────────────────────────────────────────
# main
# ─────────────────────────────────────────

def main():
    src_yaml = sys.argv[1]
    dst_pptx = sys.argv[2]

    # style.yaml 로드 (최우선)
    load_style()

    data = yaml.safe_load(Path(src_yaml).read_text(encoding="utf-8"))

    if not Path(TEMPLATE_PATH).exists():
        print(f"warning: template not found at {TEMPLATE_PATH}", file=sys.stderr)
        return

    src_prs = Presentation(TEMPLATE_PATH)
    src_slides = list(src_prs.slides)

    out_prs = Presentation(TEMPLATE_PATH)
    xml_slides = out_prs.slides._sldIdLst
    for sld in list(xml_slides):
        xml_slides.remove(sld)

    print(f"template loaded: {TEMPLATE_PATH}")
    print(f"견본 슬라이드 개수: {len(src_slides)}")

    for sd in data.get("슬라이드", []):
        kind = sd.get("종류", "본문")
        title = sd.get("제목", "")
        if kind == "결론" and ("감사" in title or "Thank" in title or "thank" in title):
            kind_eff = "감사"
        else:
            kind_eff = kind

        sample_1based = SAMPLE_MAP_1BASED.get(kind_eff, 13)
        sample_idx_0 = sample_1based - 1
        if sample_idx_0 >= len(src_slides):
            sample_idx_0 = 12
        src_slide = src_slides[sample_idx_0]

        new_slide = duplicate_slide(out_prs, src_slide)

        if kind_eff == "표지":
            fill_cover(new_slide, sd)
        elif kind_eff == "목차":
            fill_toc(new_slide, sd)
        elif kind_eff == "간지":
            fill_section_divider(new_slide, sd)
        elif kind_eff == "회사소개":
            fill_company_intro(new_slide, sd)
        elif kind_eff == "감사":
            fill_thanks(new_slide, sd)
        else:
            fill_content(new_slide, sd)

        add_notes(new_slide, sd.get("발표자_노트", ""))

    out_prs.save(dst_pptx)
    print(f"saved: {dst_pptx}")

    # zip 중복 파일 제거 (LibreOffice 호환성)
    n_removed = dedupe_pptx(dst_pptx)
    if n_removed:
        print(f"dedupe: {n_removed} duplicate file(s) removed")


def dedupe_pptx(path):
    """pptx zip 내부 중복 파일 제거.
    같은 이름의 항목이 여러 개 있으면 마지막 위치의 항목만 유지.
    LibreOffice는 중복을 거부하므로 PowerPoint 호환 + LibreOffice 호환 동시 보장."""
    tmp = path + ".dedup.tmp"
    n_removed = 0
    with zipfile.ZipFile(path, 'r') as zin:
        infos = zin.infolist()
        last_idx = {}
        for i, info in enumerate(infos):
            last_idx[info.filename] = i

        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for i, info in enumerate(infos):
                if last_idx[info.filename] != i:
                    n_removed += 1
                    continue
                with zin.open(info) as src:
                    data = src.read()
                # ZipInfo를 재사용하면 압축 메타가 보존됨
                new_info = zipfile.ZipInfo(filename=info.filename,
                                            date_time=info.date_time)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                new_info.external_attr = info.external_attr
                zout.writestr(new_info, data)

    os.replace(tmp, path)
    return n_removed


if __name__ == "__main__":
    main()
