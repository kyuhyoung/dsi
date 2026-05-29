#!/usr/bin/env python3
"""HWPX 양식 + fills.yaml → 채워진 .hwpx (XML 결정적 편집).

원칙 (memory/feedback_xml_fill.md, feedback_form_principle.md):
    양식 절대 안 만짐. 빈 셀에 텍스트만 박음.
    한컴 COM 미사용. zip + lxml 만으로 결정적 동작.

용법:
    python scripts/fill_hwpx_form.py <form.hwpx> <fills.yaml> <output.hwpx>

fills.yaml 스키마:
    fills:
      - id: T{table_idx}_R{row}_C{col}
        text: "채울 텍스트"
      - id: T{table_idx}_R{row}_C{col}
        operation: insert_image
        image_path: "kb/company/dabeeo/images/org_chart.png"  # 상대 경로 또는 절대 경로

알고리즘:
    1. .hwpx zip 풀어 Contents/section*.xml 파싱
    2. hp:tbl 순서대로 table_idx 부여 (0-based)
    3. 각 hp:tc 의 hp:cellAddr 로 (row, col) 확인
    4. fills 명세와 id 매칭:
       - operation=replace_text (기본): 셀의 첫 hp:p > hp:run > hp:t 텍스트 교체
       - operation=insert_image: 셀에 hp:pic 요소 삽입, BinData에 이미지 추가
       - operation=check/uncheck: 체크박스 토글
    5. zip 다시 묶음. 다른 파일·메타 변경 없음.

일반화:
    표/셀 좌표는 hp:cellAddr 명시값 사용. 양식 종류 무관.
    fills.yaml id 형식만 맞으면 동작.
    이미지 삽입은 KB 경로 기반 — 특정 양식/회사에 하드코딩 없음.
"""
import re
import sys
import copy
import shutil
import tempfile
import zipfile
import yaml
import random
from pathlib import Path
from lxml import etree
from PIL import Image


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hp": HP_NS, "hh": HH_NS, "hc": HC_NS}
CELL_ID_RE = re.compile(r"^T(\d+)_R(\d+)_C(\d+)$")

# HWPX 단위: 1 hwpunit = 7200 * 1/inch (약 0.01mm)
# 1 inch = 7200 hwpunit, 1 pixel (96dpi) = 75 hwpunit
HWPUNIT_PER_PIXEL = 75

# 녹색 글자 스타일 ID (fill_hwpx에서 header.xml에 추가 후 설정)
GREEN_CHAR_PR_ID = None
CELL_PARA_ID_RE = re.compile(r"^T(\d+)_R(\d+)_C(\d+)_P(\d+)$")
PARA_ID_RE = re.compile(r"^P(\d+)$")

# 양식 placeholder 채움 문자열 패턴 (단락 복제 시 치환 대상).
# templates/system_defaults.yaml 의 hwpx_fill.placeholder_filler_pattern 으로 덮어씀.
# (아래는 yaml 로드 실패 시 안전 fallback — 정본은 yaml)
PLACEHOLDER_FILLER_RE = re.compile(r"가나다라?|[○]{2,}")
# 잔존 단독 마커 정리용. yaml hwpx_fill.marker_only_pattern 으로 덮어씀.
MARKER_ONLY_RE = re.compile(r"^[\s\*\-·○□❍•─━]+$")

# 채운 셀의 row 고정높이 자동 해제 정책 (한컴이 content 기반 재계산하도록).
# yaml hwpx_fill.cell_height_release.{enabled,threshold,min_height} 로 덮어씀.
CELL_HEIGHT_RELEASE_ENABLED = True
CELL_HEIGHT_RELEASE_THRESHOLD = 3000  # HWPX 단위. 1줄 ≈ 850
CELL_HEIGHT_RELEASE_MIN = 850


def parse_cell_id(cell_id: str):
    m = CELL_ID_RE.match(cell_id)
    if not m:
        raise ValueError(f"잘못된 cell id: {cell_id!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def parse_cell_para_id(cid: str):
    m = CELL_PARA_ID_RE.match(cid)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def parse_para_id(pid: str):
    m = PARA_ID_RE.match(pid)
    if not m:
        return None
    return int(m.group(1))


def resolve_image_path(image_ref: str, project_root: Path = None) -> Path:
    """이미지 경로 해석. 상대 경로면 프로젝트 루트 기준.

    일반화: KB 구조(kb/company/*/images/)나 절대 경로 모두 지원.
    특정 회사/양식에 하드코딩 없음.
    """
    p = Path(image_ref)
    if p.is_absolute() and p.exists():
        return p

    # 상대 경로: 프로젝트 루트 기준
    if project_root is None:
        project_root = Path(__file__).parent.parent

    resolved = project_root / image_ref
    if resolved.exists():
        return resolved

    # 못 찾으면 None (호출자가 처리)
    return None


def load_image_schema(project_root: Path = None) -> dict:
    """KB 이미지 스키마 로드.

    Returns:
        스키마 dict 또는 빈 dict (스키마 없으면)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    schema_path = project_root / "kb" / "image_schema.yaml"
    if not schema_path.exists():
        return {}

    try:
        return yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def normalize_keyword(text: str) -> str:
    """키워드 정규화: 공백/특수문자 제거, 소문자화."""
    import unicodedata
    # 공백 정규화
    text = re.sub(r"\s+", "", text)
    # 특수문자 제거 (한글/영문/숫자만 유지)
    text = re.sub(r"[^\w가-힣]", "", text, flags=re.UNICODE)
    return text.lower()


def search_kb_image(context: str, company: str = None, project_root: Path = None) -> Path:
    """KB에서 컨텍스트에 맞는 이미지 검색.

    일반화: image_schema.yaml 기반 키워드 매칭.
    특정 양식/회사에 하드코딩 없음.

    Args:
        context: 검색 컨텍스트 (셀의 hints.left, table_label 등)
        company: 회사명 (kb/company/{company}/images/ 경로용)
        project_root: 프로젝트 루트

    Returns:
        이미지 경로 (Path) 또는 None (못 찾으면)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    schema = load_image_schema(project_root)
    if not schema:
        return None

    # 컨텍스트 정규화
    norm_context = normalize_keyword(context)

    # 공통 매핑에서 검색
    mappings = schema.get("common_mappings", [])

    best_match = None
    best_priority = float("inf")

    for mapping in mappings:
        keywords = mapping.get("keywords", [])
        for kw in keywords:
            norm_kw = normalize_keyword(kw)
            if norm_kw in norm_context or norm_context in norm_kw:
                priority = mapping.get("priority", 10)
                if priority < best_priority:
                    best_match = mapping
                    best_priority = priority

    if best_match is None:
        return None

    # 1순위: 큐레이트된 의미명 파일 (사람이 배치한 정확한 이미지)
    primary = _resolve_kb_path(best_match.get("image_path", ""), company, project_root)
    if primary:
        return primary

    # 2순위: extracted/index.yaml 컨텍스트 매칭 (deck 자체 텍스트로 일반 검색)
    indexed = _search_index_image(best_match.get("keywords", []), company,
                                  project_root, schema.get("search_config", {}))
    if indexed:
        return indexed

    # 3순위: 스키마 fallback 경로 (약한 추정)
    for path_template in best_match.get("fallback_paths", []):
        fb = _resolve_kb_path(path_template, company, project_root)
        if fb:
            return fb

    return None


def _company_list(company: str, project_root: Path) -> list:
    """검색 대상 회사 목록. company 지정 시 그것만, 아니면 kb/company/* 전부."""
    if company:
        return [company]
    company_dir = project_root / "kb" / "company"
    if company_dir.exists():
        return [s.name for s in company_dir.iterdir() if s.is_dir()]
    return []


def _resolve_kb_path(path_template: str, company: str, project_root: Path):
    """{company} 치환 후 존재하는 파일 Path 반환 (없으면 None)."""
    if not path_template:
        return None
    for c in _company_list(company, project_root):
        resolved = project_root / path_template.replace("{company}", c)
        if resolved.exists():
            return resolved
    return None


# 한컴이 직접 렌더 가능한 래스터 형식만 (wdp/emf/svg 등 제외)
_RASTER_EXTS = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]


def _search_index_image(keywords: list, company: str, project_root: Path,
                        search_config: dict = None):
    """extracted/index.yaml 에서 키워드 매칭으로 최적 이미지 검색.

    일반화: 추출 이미지의 출처 슬라이드 텍스트(context_text)에 스키마 키워드가
    몇 개 나타나는지로 점수. 특정 이미지명·회사 하드코딩 없음 — 임의 회사 KB 동작.
    점수 우선, 동점이면 큰 파일(주요 도식일 확률 높음).
    크기 bound 는 image_schema.yaml 의 search_config 에서 로드 (매직넘버 박지 않음).
    """
    search_config = search_config or {}
    min_bytes = search_config.get("index_min_bytes", 0)
    max_bytes = search_config.get("index_max_bytes", float("inf"))
    latin_min = search_config.get("index_latin_min_len", 0)

    norm_kws = [normalize_keyword(k) for k in keywords if k]
    # 순수 영문 짧은 키워드 제외 (substring 오탐 방지). 한글 포함 키워드는 유지.
    norm_kws = [k for k in norm_kws
                if k and (re.search(r"[가-힣]", k) or len(k) >= latin_min)]
    if not norm_kws:
        return None

    best_path, best_score, best_size = None, 0, -1
    for c in _company_list(company, project_root):
        extracted = project_root / "kb" / "company" / c / "images" / "extracted"
        index_path = extracted / "index.yaml"
        if not index_path.exists():
            continue
        try:
            with open(index_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        for entry in data.get("images", []):
            ctx = normalize_keyword(entry.get("context_text", ""))
            if not ctx:
                continue
            score = sum(1 for k in norm_kws if k in ctx)
            if score == 0:
                continue
            img_file = extracted / entry.get("file", "")
            if img_file.suffix.lower() not in _RASTER_EXTS or not img_file.exists():
                continue
            size = img_file.stat().st_size
            if size < min_bytes or size > max_bytes:
                continue
            if score > best_score or (score == best_score and size > best_size):
                best_path, best_score, best_size = img_file, score, size
    return best_path


def get_image_dimensions(image_path: Path) -> tuple:
    """이미지 파일의 (width, height) 픽셀 크기 반환."""
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception:
        return (100, 100)  # 기본값


def get_next_image_id(td_path: Path) -> tuple:
    """다음 사용 가능한 이미지 ID와 경로 반환.

    Returns:
        (image_id: str, bin_path: str) - 예: ("image2", "BinData/image2.png")
    """
    bindata_dir = td_path / "BinData"
    if not bindata_dir.exists():
        bindata_dir.mkdir(parents=True)
        return "image1", "BinData/image1"

    existing = list(bindata_dir.glob("image*.*"))
    max_num = 0
    for f in existing:
        m = re.match(r"image(\d+)", f.stem)
        if m:
            max_num = max(max_num, int(m.group(1)))

    new_num = max_num + 1
    return f"image{new_num}", f"BinData/image{new_num}"


def add_image_to_bindata(td_path: Path, src_image: Path) -> str:
    """이미지를 BinData 폴더에 복사하고 image ID 반환.

    Returns:
        image_id (str) - content.hpf에 등록할 ID (예: "image2")
    """
    image_id, bin_path_base = get_next_image_id(td_path)
    suffix = src_image.suffix.lower()

    # HWPX가 지원하는 형식으로 변환 (필요시)
    if suffix in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
        dest_path = td_path / f"{bin_path_base}{suffix}"
    else:
        # 지원 안 되는 형식은 PNG로 변환
        dest_path = td_path / f"{bin_path_base}.png"
        suffix = ".png"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_image, dest_path)

    return image_id, suffix


def update_content_hpf(td_path: Path, image_id: str, suffix: str):
    """content.hpf에 새 이미지 항목 추가."""
    hpf_path = td_path / "Contents" / "content.hpf"
    if not hpf_path.exists():
        return False

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(hpf_path), parser)
    root = tree.getroot()

    # manifest 찾기
    OPF_NS = "http://www.idpf.org/2007/opf/"
    manifest = root.find(f".//{{{OPF_NS}}}manifest")
    if manifest is None:
        return False

    # 미디어 타입 결정
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }
    media_type = media_types.get(suffix, "image/png")

    # 새 item 추가
    item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
    item.set("id", image_id)
    item.set("href", f"BinData/{image_id}{suffix}")
    item.set("media-type", media_type)
    item.set("isEmbeded", "1")

    # 저장
    body = etree.tostring(root, encoding="unicode")
    xml_header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    hpf_path.write_bytes((xml_header + body).encode("utf-8"))
    return True


def create_pic_element(image_id: str, width_px: int, height_px: int, cell_width_hwp: int = None) -> etree.Element:
    """hp:pic 요소 생성.

    일반화: 이미지 크기를 셀 너비에 맞게 자동 조정.
    """
    # 픽셀 → hwpunit 변환
    org_width = width_px * HWPUNIT_PER_PIXEL
    org_height = height_px * HWPUNIT_PER_PIXEL

    # 셀 너비에 맞게 스케일 (셀 너비가 주어진 경우)
    if cell_width_hwp and org_width > cell_width_hwp:
        scale = cell_width_hwp / org_width
        cur_width = int(org_width * scale)
        cur_height = int(org_height * scale)
    else:
        cur_width = org_width
        cur_height = org_height

    # 고유 ID 생성
    pic_id = random.randint(1000000000, 9999999999)
    inst_id = random.randint(1000000000, 9999999999)

    pic = etree.Element(f"{{{HP_NS}}}pic")
    pic.set("id", str(pic_id))
    pic.set("zOrder", "0")
    pic.set("numberingType", "PICTURE")
    pic.set("textWrap", "TOP_AND_BOTTOM")
    pic.set("textFlow", "BOTH_SIDES")
    pic.set("lock", "0")
    pic.set("dropcapstyle", "None")
    pic.set("href", "")
    pic.set("groupLevel", "0")
    pic.set("instid", str(inst_id))
    pic.set("reverse", "0")

    # offset
    offset = etree.SubElement(pic, f"{{{HP_NS}}}offset")
    offset.set("x", "0")
    offset.set("y", "0")

    # orgSz
    org_sz = etree.SubElement(pic, f"{{{HP_NS}}}orgSz")
    org_sz.set("width", str(org_width))
    org_sz.set("height", str(org_height))

    # curSz
    cur_sz = etree.SubElement(pic, f"{{{HP_NS}}}curSz")
    cur_sz.set("width", str(cur_width))
    cur_sz.set("height", str(cur_height))

    # flip
    flip = etree.SubElement(pic, f"{{{HP_NS}}}flip")
    flip.set("horizontal", "0")
    flip.set("vertical", "0")

    # rotationInfo
    rot = etree.SubElement(pic, f"{{{HP_NS}}}rotationInfo")
    rot.set("angle", "0")

    # renderingInfo
    render = etree.SubElement(pic, f"{{{HP_NS}}}renderingInfo")
    for matrix_name in ["transMatrix", "scaMatrix", "rotMatrix"]:
        mat = etree.SubElement(render, f"{{{HC_NS}}}{matrix_name}")
        if matrix_name == "scaMatrix":
            scale_x = cur_width / org_width if org_width else 1
            scale_y = cur_height / org_height if org_height else 1
            mat.set("e1", f"{scale_x:.6f}")
            mat.set("e5", f"{scale_y:.6f}")
        else:
            mat.set("e1", "1")
            mat.set("e5", "1")
        mat.set("e2", "0")
        mat.set("e3", "0")
        mat.set("e4", "0")
        mat.set("e6", "0")

    # imgRect
    img_rect = etree.SubElement(pic, f"{{{HP_NS}}}imgRect")
    for i, (px, py) in enumerate([(0, 0), (org_width, 0), (org_width, org_height), (0, org_height)]):
        pt = etree.SubElement(img_rect, f"{{{HC_NS}}}pt{i}")
        pt.set("x", str(int(px)))
        pt.set("y", str(int(py)))

    # imgClip
    img_clip = etree.SubElement(pic, f"{{{HP_NS}}}imgClip")
    img_clip.set("left", "0")
    img_clip.set("right", str(org_width))
    img_clip.set("top", "0")
    img_clip.set("bottom", str(org_height))

    # inMargin
    in_margin = etree.SubElement(pic, f"{{{HP_NS}}}inMargin")
    for side in ["left", "right", "top", "bottom"]:
        in_margin.set(side, "0")

    # img (이미지 참조)
    img = etree.SubElement(pic, f"{{{HC_NS}}}img")
    img.set("binaryItemIDRef", image_id)
    img.set("bright", "0")
    img.set("contrast", "0")
    img.set("effect", "REAL_PIC")
    img.set("alpha", "0")

    # effects
    etree.SubElement(pic, f"{{{HP_NS}}}effects")

    # sz
    sz = etree.SubElement(pic, f"{{{HP_NS}}}sz")
    sz.set("width", str(cur_width))
    sz.set("widthRelTo", "ABSOLUTE")
    sz.set("height", str(cur_height))
    sz.set("heightRelTo", "ABSOLUTE")
    sz.set("protect", "0")

    # pos
    pos = etree.SubElement(pic, f"{{{HP_NS}}}pos")
    pos.set("treatAsChar", "1")  # 글자처럼 취급 (셀 안에 맞춤)
    pos.set("affectLSpacing", "0")
    pos.set("flowWithText", "1")
    pos.set("allowOverlap", "0")
    pos.set("holdAnchorAndSO", "0")
    pos.set("vertRelTo", "PARA")
    pos.set("horzRelTo", "COLUMN")
    pos.set("vertAlign", "TOP")
    pos.set("horzAlign", "LEFT")
    pos.set("vertOffset", "0")
    pos.set("horzOffset", "0")

    # outMargin
    out_margin = etree.SubElement(pic, f"{{{HP_NS}}}outMargin")
    for side in ["left", "right", "top", "bottom"]:
        out_margin.set(side, "0")

    return pic


def insert_image_to_cell(tc_el, image_id: str, width_px: int, height_px: int) -> bool:
    """셀에 이미지 삽입. 기존 텍스트는 제거하고 hp:pic 요소 추가.

    일반화: 셀 구조(hp:subList > hp:p > hp:run)를 동적으로 처리.
    """
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return False

    # 셀 너비 추출 (hp:cellSz)
    cell_sz = tc_el.find(f"{{{HP_NS}}}cellSz")
    cell_width = None
    if cell_sz is not None:
        cell_width = int(cell_sz.get("width", "0"))

    # 첫 번째 p 찾기 또는 생성
    p = subList.find(f"{{{HP_NS}}}p")
    if p is None:
        p = etree.SubElement(subList, f"{{{HP_NS}}}p")

    # 기존 run들 제거 (플레이스홀더 텍스트 제거)
    for old_run in p.findall(f"{{{HP_NS}}}run"):
        p.remove(old_run)

    # hp:pic 요소 생성 및 삽입
    pic = create_pic_element(image_id, width_px, height_px, cell_width)

    # run 안에 pic 삽입 (한컴 구조)
    new_run = etree.SubElement(p, f"{{{HP_NS}}}run")
    new_run.append(pic)

    # linesegarray 삭제 (한컴 재계산)
    ls = p.find(f"{{{HP_NS}}}linesegarray")
    if ls is not None:
        p.remove(ls)

    return True


def build_cell_index(section_root):
    """section XML 안의 모든 표·셀을 (table_idx, row, col) → hp:tc element 로 매핑.

    table_idx 는 *문서 순서대로 등장하는 hp:tbl 의 0-based 인덱스*.
    row, col 은 hp:cellAddr 의 rowAddr/colAddr 명시값.
    """
    index = {}
    tables = section_root.iter(f"{{{HP_NS}}}tbl")
    for t_idx, tbl in enumerate(tables):
        for tr in tbl.findall(f"{{{HP_NS}}}tr"):
            for tc in tr.findall(f"{{{HP_NS}}}tc"):
                addr = tc.find(f"{{{HP_NS}}}cellAddr")
                if addr is None:
                    continue
                row = int(addr.get("rowAddr"))
                col = int(addr.get("colAddr"))
                index[(t_idx, row, col)] = tc
    return index


def find_char_style_ref(tc_el):
    """셀 또는 부모에서 charPrIDRef 찾기 (글자 스타일 참조)."""
    # 1. 같은 셀 안의 기존 run에서 찾기
    for run in tc_el.iter(f"{{{HP_NS}}}run"):
        ref = run.get("charPrIDRef")
        if ref:
            return ref
    # 2. 부모 tr의 다른 셀에서 찾기
    tr = tc_el.getparent()
    if tr is not None:
        for sibling_tc in tr.findall(f"{{{HP_NS}}}tc"):
            for run in sibling_tc.iter(f"{{{HP_NS}}}run"):
                ref = run.get("charPrIDRef")
                if ref:
                    return ref
    return None


def set_cell_text(tc_el, text: str):
    """hp:tc 안 첫 hp:p 의 텍스트 *통째 교체*.

    set_paragraph_text 와 동일 원칙:
      - 기존 run 전부 제거 (원본 라벨·안내문 placeholder 잔존 방지)
      - 새 run 1개 생성 후 텍스트 박음
      - stale linesegarray 삭제 → 한컴이 열 때 줄바꿈 재계산
        (안 지우면 짧은 placeholder 기준 1줄 세그먼트에 긴 텍스트를 욱여넣어 글자 겹침)

    주의: 양식 원본 텍스트 (라벨 등) 도 통째로 덮어씀.
    체크박스 셀처럼 원본 일부만 바꾸려면 apply_cell_check 사용.
    """
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return False
    p = subList.find(f"{{{HP_NS}}}p")
    if p is None:
        p = etree.SubElement(subList, f"{{{HP_NS}}}p")

    # 기존 run charPrIDRef 백업 (녹색 미사용 시 원본 서식 유지)
    first_run = p.find(f"{{{HP_NS}}}run")
    orig_char_pr = first_run.get("charPrIDRef") if first_run is not None else None

    # 기존 run 전부 제거 (placeholder 잔존 방지)
    for old_run in p.findall(f"{{{HP_NS}}}run"):
        p.remove(old_run)

    run = etree.SubElement(p, f"{{{HP_NS}}}run")
    char_pr = str(GREEN_CHAR_PR_ID) if GREEN_CHAR_PR_ID is not None else orig_char_pr
    if char_pr is not None:
        run.set("charPrIDRef", char_pr)

    t = etree.SubElement(run, f"{{{HP_NS}}}t")
    t.text = text

    # stale linesegarray 삭제 (한컴 재계산)
    ls = p.find(f"{{{HP_NS}}}linesegarray")
    if ls is not None:
        p.remove(ls)
    return True


def apply_cell_check(tc_el, mode: str = "check"):
    """체크박스 셀의 *원본 텍스트 보존* + □/☐ → ☑ (또는 ☑/☒ → □) 만 부분 교체.

    양식 라벨 절대 안 변경. 예: "□ 여" → "☑ 여" (라벨 "여" 보존).
    """
    subList = tc_el.find(f"{{{HP_NS}}}subList")
    if subList is None:
        return False
    changed = False
    for t in tc_el.iter(f"{{{HP_NS}}}t"):
        if t.text is None:
            continue
        if mode == "check":
            new = t.text.replace("□", "☑").replace("☐", "☑")
        elif mode == "uncheck":
            new = t.text.replace("☑", "□").replace("☒", "□")
        else:
            new = t.text
        if new != t.text:
            t.text = new
            changed = True
    return changed


def build_paragraph_index(section_root):
    """최상위 hp:p 만 → p_idx → hp:p element 매핑."""
    return {i: p for i, p in enumerate(section_root.findall(f"{{{HP_NS}}}p"))}


def set_paragraph_text(p_el, text: str):
    """hp:p 안 텍스트를 통째 교체. 기존 run들 제거 후 새 run 생성.

    여러 줄 text 는 첫 줄만 박음 (단순 PoC). 본격은 hp:p 통째 복제 + 다중 단락.
    """
    # 기존 run들에서 charPrIDRef 백업 (첫 번째 것 사용)
    first_run = p_el.find(f"{{{HP_NS}}}run")
    if first_run is None:
        return False

    # 기존 모든 run 제거 (원본 "가나다" 등 placeholder 잔존 방지)
    for old_run in p_el.findall(f"{{{HP_NS}}}run"):
        p_el.remove(old_run)

    # 새 run 생성
    new_run = etree.SubElement(p_el, f"{{{HP_NS}}}run")
    # 녹색 charPrIDRef 설정
    if GREEN_CHAR_PR_ID is not None:
        new_run.set("charPrIDRef", str(GREEN_CHAR_PR_ID))

    t = etree.SubElement(new_run, f"{{{HP_NS}}}t")
    t.text = text

    # linesegarray 삭제 (한컴 재계산)
    ls = p_el.find(f"{{{HP_NS}}}linesegarray")
    if ls is not None:
        p_el.remove(ls)
    return True


def _norm_for_header_match(s: str) -> str:
    """헤더 매칭용 정규화 — 공백·하이픈·언더스코어·중점 제거 + 소문자.
    "As is" / "[To-be]" / "To  be" 모두 동일 정규형으로 매칭."""
    return re.sub(r"[\s\-_·]+", "", (s or "")).lower()


def _detect_column_mismap(tc_el, new_text: str):
    """채울 내용에 *다른 컬럼의 헤더* 가 마커(`[X]`/`(X)`/`X:`)로 들어있으면 mis-mapping 의심.
    예: As is 컬럼 셀(C0)에 채우는 텍스트에 `[To-be]` 가 있으면 → C1(To be) 컬럼 내용이 잘못 들어감.

    일반: 비교 표(As-Is/To-Be·이전/이후·입력/출력·국내/해외 등) 컬럼 매핑 오류를
    *양식의 컬럼 헤더 자체에서 학습*해 검출 — 특정 헤더명·내용 하드코딩 없음.
    반환: mismap 감지된 *다른 헤더* 텍스트(거부 이유), 없으면 None.
    """
    # 부모 tbl
    el = tc_el.getparent()
    while el is not None and etree.QName(el).localname != "tbl":
        el = el.getparent()
    if el is None:
        return None
    trs = el.findall(f"{{{HP_NS}}}tr")
    if len(trs) < 2:
        return None  # 헤더+본문 최소 2행 필요
    # row 0 = 컬럼 헤더
    header_tcs = trs[0].findall(f"{{{HP_NS}}}tc")
    headers = ["".join((t.text or "") for t in tc.iter(f"{{{HP_NS}}}t")).strip()
               for tc in header_tcs]
    if len([h for h in headers if h]) < 2:
        return None  # 의미 있는 헤더 2개 미만
    # 채우는 셀의 column index
    tr = tc_el.getparent()
    if tr is None:
        return None
    my_tcs = tr.findall(f"{{{HP_NS}}}tc")
    try:
        my_col = my_tcs.index(tc_el)
    except ValueError:
        return None
    # 자기 컬럼 헤더 빼고 다른 헤더와 비교 (header row 자체는 skip)
    if tr is trs[0]:
        return None
    my_header_norm = _norm_for_header_match(headers[my_col] if my_col < len(headers) else "")
    new_norm = _norm_for_header_match(new_text)
    # `[X]`/`(X)`/`X:` 형태 마커 추출
    markers = re.findall(r"[\[(]([^\[\]()]{1,30})[\])]|([^\s]{1,30}):", new_text or "")
    extracted = [_norm_for_header_match(a or b) for a, b in markers]
    extracted = [m for m in extracted if m]
    for i, h in enumerate(headers):
        if i == my_col or not h:
            continue
        h_norm = _norm_for_header_match(h)
        if h_norm == my_header_norm:
            continue
        if h_norm and h_norm in extracted:
            return h
    return None


def _is_standalone_instruction_box(tc_el) -> bool:
    """tc 가 *1×1 단일셀 표*의 셀이고, 텍스트가 ※ 로 시작하는 안내문이면 True.
    이는 standalone 작성요령 box — *내용으로 채우면 안 됨*(양식 안내문, 제출 시 삭제 대상).
    일반: 한국 공공 양식 공통 관행(단일 셀 ※ 박스 = 안내). 다중 셀(요약 표)은 입력칸.
    """
    # 부모 tbl 찾기 (tc → tr → tbl)
    el = tc_el.getparent()
    while el is not None and etree.QName(el).localname != "tbl":
        el = el.getparent()
    if el is None:
        return False
    trs = el.findall(f"{{{HP_NS}}}tr")
    if len(trs) != 1:
        return False
    tcs = trs[0].findall(f"{{{HP_NS}}}tc")
    if len(tcs) != 1:
        return False
    txt = "".join((t.text or "") for t in tc_el.iter(f"{{{HP_NS}}}t")).strip()
    return bool(txt) and txt.startswith("※")


def _load_fill_config(project_root: Path):
    """templates/system_defaults.yaml 의 hwpx_fill 설정 로드 (filler·marker_only 패턴 등)."""
    global PLACEHOLDER_FILLER_RE, MARKER_ONLY_RE
    global CELL_HEIGHT_RELEASE_ENABLED, CELL_HEIGHT_RELEASE_THRESHOLD, CELL_HEIGHT_RELEASE_MIN
    try:
        cfg_path = project_root / "templates" / "system_defaults.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        hf = cfg.get("hwpx_fill") or {}
        if hf.get("placeholder_filler_pattern"):
            PLACEHOLDER_FILLER_RE = re.compile(hf["placeholder_filler_pattern"])
        if hf.get("marker_only_pattern"):
            MARKER_ONLY_RE = re.compile(hf["marker_only_pattern"])
        rel = hf.get("cell_height_release") or {}
        if "enabled" in rel:
            CELL_HEIGHT_RELEASE_ENABLED = bool(rel["enabled"])
        if "threshold" in rel:
            CELL_HEIGHT_RELEASE_THRESHOLD = int(rel["threshold"])
        if "min_height" in rel:
            CELL_HEIGHT_RELEASE_MIN = int(rel["min_height"])
    except Exception:
        pass  # fallback 유지


def _shrink_height_attr(el, threshold: int, min_h: int) -> bool:
    """el 의 height attribute 가 threshold 초과면 min_h 로 축소. 변경 시 True."""
    if el is None:
        return False
    h_str = el.get("height")
    if not h_str:
        return False
    try:
        h = int(h_str)
    except (TypeError, ValueError):
        return False
    if h > threshold:
        el.set("height", str(min_h))
        return True
    return False


def release_cell_height_locks(filled_tcs) -> int:
    """채운 셀의 cellSz/@height + 그 셀이 속한 표의 hp:sz/@height 가 임계 초과면 min_h 로 축소.
    한컴이 row·표 높이를 *내용 기반*으로 자동 재계산하도록 absolute height lock 해제.

    근본 치유: 원본 양식은 placeholder 분량 기준 절대 높이를 *두 곳* 에 박아둠 —
    (a) hp:tbl/hp:sz/@height (표 전체 box) (b) hp:tc/hp:cellSz/@height (셀 단위).
    cellSz 만 줄여도 *표 sz* 가 크면 한컴이 표 영역을 그 크기로 그려 row 가 안 줄어듬.
    *두 곳 모두* 해제해야 한컴이 콘텐츠 기반 재계산 → 표 페이지 안 수렴.

    채운 셀만 해제 → 양식 라벨·시스템 셀의 디자인은 보존.
    임의 양식·회사·RFP 동일 동작. 룰 임계값은 yaml 정본.

    Returns: 변경된 height attribute 개수 (셀 + 표).
    """
    if not CELL_HEIGHT_RELEASE_ENABLED:
        return 0
    released = 0
    seen_tc = set()
    seen_tbl = set()
    for tc in filled_tcs:
        if tc is None:
            continue
        tid = id(tc)
        if tid in seen_tc:
            continue
        seen_tc.add(tid)
        # (a) 셀 cellSz 축소
        cz = tc.find(f"{{{HP_NS}}}cellSz")
        if _shrink_height_attr(cz, CELL_HEIGHT_RELEASE_THRESHOLD, CELL_HEIGHT_RELEASE_MIN):
            released += 1
        # (b) 같은 표의 sz 축소 — 표마다 1회
        # 주의: lxml iterancestors 결과를 *바로* tbl.find 에 쓰면 일부 케이스에서 None 반환
        # → 한 차례 itertext() 호출로 tree state 안정화. (검증 가설: lxml 내부 캐시 이슈)
        tbl = None
        for anc in tc.iterancestors(f"{{{HP_NS}}}tbl"):
            tbl = anc
            break
        if tbl is None:
            continue
        _ = "".join(tbl.itertext())  # tree 안정화 — 이 줄 없으면 find(sz) 가 None
        if id(tbl) in seen_tbl:
            continue
        seen_tbl.add(id(tbl))
        tsz = tbl.find(f"{{{HP_NS}}}sz")
        if _shrink_height_attr(tsz, CELL_HEIGHT_RELEASE_THRESHOLD, CELL_HEIGHT_RELEASE_MIN):
            released += 1
    # (c) 채운 셀 안 *완전 빈 단락* 자체를 제거 — 빈 단락이 자리 차지하면 row 가 그만큼
    # 잡힘. cellSz/sz 줄여도 한컴 layout 은 *셀 안 단락 개수* 로 row 자리 산정.
    # 채운 셀 안의 미사용 placeholder 단락(텍스트 비움 후) 도 함께 정리해야 row 가 콘텐츠
    # 기반으로 줄어듦. 단, 셀의 *마지막 단락 하나*는 보존 (한컴 표 셀 구조 요건).
    seen_tc2 = set()
    for tc in filled_tcs:
        if tc is None:
            continue
        tid = id(tc)
        if tid in seen_tc2:
            continue
        seen_tc2.add(tid)
        sub = tc.find(f"{{{HP_NS}}}subList")
        if sub is None:
            continue
        ps = sub.findall(f"{{{HP_NS}}}p")
        # 마지막 1개 빈 단락은 셀 구조 요건상 남김
        empty_ps = []
        for p in ps:
            ts = list(p.iter(f"{{{HP_NS}}}t"))
            stripped = "".join((t.text or "") for t in ts).strip()
            if not stripped:
                empty_ps.append(p)
        # 마지막 1개 보존, 나머지 제거
        to_remove = empty_ps[:-1] if empty_ps else []
        for p in to_remove:
            sub.remove(p)
            released += 1
        # 보존되는 마지막 빈 단락의 linesegarray 도 제거 (자리 안 잡게)
        if empty_ps:
            keeper = empty_ps[-1]
            ls = keeper.find(f"{{{HP_NS}}}linesegarray")
            if ls is not None:
                keeper.remove(ls)
                released += 1
    return released


def cleanup_residual_placeholders(section_root) -> int:
    """Fill 후 *미채움 placeholder 잔존*을 자동 정리 (텍스트 비움).
    잡는 케이스 (yaml 패턴 기반):
      - PLACEHOLDER_FILLER_RE 매칭 (가나다·○○○ 등 채움 문자열)
      - MARKER_ONLY_RE 매칭 + 짧음 (단독 ❍/-/*/□ 등 마커만 남음)
    일반: 양식·회사 무관, 모든 hp:p 스캔. 양식 라벨에 우연 단순 마커는 길이 한도(≤5)로 보호.
    """
    cleaned = 0
    for p in section_root.iter(f"{{{HP_NS}}}p"):
        ts = list(p.iter(f"{{{HP_NS}}}t"))
        if not ts:
            continue
        txt = "".join((t.text or "") for t in ts)
        stripped = txt.strip()
        if not stripped:
            continue
        matched = False
        if PLACEHOLDER_FILLER_RE.search(stripped):
            matched = True
        elif len(stripped) <= 5 and MARKER_ONLY_RE.match(stripped):
            matched = True
        if matched:
            for t in ts:
                if t.text:
                    t.text = ""
            ls = p.find(f"{{{HP_NS}}}linesegarray")
            if ls is not None:
                p.remove(ls)
            cleaned += 1
    return cleaned


def _para_plain_text(p_el) -> str:
    return "".join((t.text or "") for t in p_el.iter(f"{{{HP_NS}}}t"))


def _leading_marker(text: str) -> str:
    """선두 공백 뒤의 불릿 마커(비-한글/영숫자 기호열) 추출. 없으면 ''.
    양식이 쓰는 마커가 무엇이든(❍/-/*/·/○…) 그대로 잡음 — 특정 문자 하드코딩 아님."""
    m = re.match(r"\s*([^\s가-힣A-Za-z0-9(\[]+)", text or "")
    return m.group(1) if m else ""


def inject_paragraphs(section_root, anchor_idx: int, lines: list) -> int:
    """anchor_idx 단락부터 *연속된 placeholder 단락*을 레벨 템플릿으로 삼아,
    lines(각 '마커 + 내용')를 복제·치환해 주입. 양식 불릿·들여쓰기 구조 보존.

    일반화: 레벨 템플릿·마커는 *양식 자체*에서 학습(복제). filler 패턴만 yaml.
    특정 양식/회사/내용 하드코딩 없음. 주의: 단락을 추가하므로 호출 후 top-level
    인덱스가 바뀜 → 호출자는 anchor 내림차순으로, 다른 fill 이후 마지막에 실행.
    """
    paras = section_root.findall(f"{{{HP_NS}}}p")
    if anchor_idx < 0 or anchor_idx >= len(paras):
        return 0
    # anchor 부터 연속된 filler placeholder 단락 = 레벨 템플릿 (❍/-/* …)
    templates = []
    i = anchor_idx
    while i < len(paras) and PLACEHOLDER_FILLER_RE.search(_para_plain_text(paras[i])):
        templates.append(paras[i])
        i += 1
    if not templates:
        return 0
    tmpl_by_marker = {}
    for tmpl in templates:
        tmpl_by_marker.setdefault(_leading_marker(_para_plain_text(tmpl)), tmpl)

    anchor = templates[0]
    parent = anchor.getparent()
    pos = list(parent).index(anchor)
    made = 0
    for line in lines:
        line = (line or "").strip()
        if not line:
            continue
        marker = _leading_marker(line)
        content = line[len(marker):].lstrip() if marker and line.startswith(marker) else line
        tmpl = tmpl_by_marker.get(marker) or templates[0]
        clone = copy.deepcopy(tmpl)
        # filler 가 든 run 의 filler 만 content 로 치환 (마커·들여쓰기 run 은 보존)
        replaced = False
        for t in clone.iter(f"{{{HP_NS}}}t"):
            if t.text and PLACEHOLDER_FILLER_RE.search(t.text):
                t.text = PLACEHOLDER_FILLER_RE.sub(lambda _m: content, t.text, count=1)
                run = t.getparent()
                if GREEN_CHAR_PR_ID is not None and run is not None:
                    run.set("charPrIDRef", str(GREEN_CHAR_PR_ID))
                replaced = True
                break
        if not replaced:
            continue
        ls = clone.find(f"{{{HP_NS}}}linesegarray")
        if ls is not None:
            clone.remove(ls)
        parent.insert(pos + made, clone)
        made += 1
    if made:
        for tmpl in templates:
            parent.remove(tmpl)
    return made


def fill_section(section_path: Path, fills: list, stats: dict, image_registry: dict = None):
    """section XML 파일을 in-place 편집. fills 적용 + stats 갱신.

    Args:
        image_registry: {cell_id: (image_id, width_px, height_px)} 이미지 삽입 정보
    """
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(section_path), parser)
    root = tree.getroot()
    cell_idx = build_cell_index(root)
    para_idx = build_paragraph_index(root)
    stats["sections_total"] = stats.get("sections_total", 0) + 1
    stats["cells_in_section"] = stats.get("cells_in_section", 0) + len(cell_idx)
    stats["paras_in_section"] = stats.get("paras_in_section", 0) + len(para_idx)

    if image_registry is None:
        image_registry = {}

    # 단락 생성(주입)은 top-level 인덱스를 바꾸므로 여기 모았다가 *루프 후* 처리
    inject_jobs = []  # [(anchor_idx, [lines])]

    # 채운 셀(tc) 추적 — 마지막에 height-lock 자동 해제 (표 페이지 초과 방지)
    filled_tcs = []

    for entry in fills:
        cid = entry.get("id", "")
        operation = entry.get("operation", "replace_text")
        text = entry.get("text", "")
        if not cid:
            continue

        # 다중 단락 주입: paragraphs 리스트가 있으면 P-id 를 anchor 로 모아둠
        para_list = entry.get("paragraphs")
        if isinstance(para_list, list) and para_list:
            pm = parse_para_id(cid)
            if pm is not None:
                inject_jobs.append((pm, para_list))
            else:
                stats["failed_id"] = stats.get("failed_id", 0) + 1
            continue

        # 이미지 삽입 처리
        if operation == "insert_image":
            try:
                t, r, c = parse_cell_id(cid)
            except ValueError:
                stats["failed_id"] = stats.get("failed_id", 0) + 1
                continue

            tc = cell_idx.get((t, r, c))
            if tc is None:
                continue

            # 이미지 정보 가져오기
            img_info = image_registry.get(cid)
            if img_info is None:
                stats["image_not_registered"] = stats.get("image_not_registered", 0) + 1
                continue

            image_id, width_px, height_px = img_info
            if insert_image_to_cell(tc, image_id, width_px, height_px):
                stats["filled_image"] = stats.get("filled_image", 0) + 1
                filled_tcs.append(tc)
            continue

        # 자동 이미지 검색 (KB 기반)
        if operation == "auto_image":
            try:
                t, r, c = parse_cell_id(cid)
            except ValueError:
                stats["failed_id"] = stats.get("failed_id", 0) + 1
                continue

            tc = cell_idx.get((t, r, c))
            if tc is None:
                continue

            # 이미지 정보 가져오기 (사전 처리에서 등록됨)
            img_info = image_registry.get(cid)
            if img_info is None:
                stats["image_auto_not_found"] = stats.get("image_auto_not_found", 0) + 1
                continue

            image_id, width_px, height_px = img_info
            if insert_image_to_cell(tc, image_id, width_px, height_px):
                stats["filled_image_auto"] = stats.get("filled_image_auto", 0) + 1
                filled_tcs.append(tc)
            continue

        if operation == "replace_text" and text == "":
            continue

        cp_match = parse_cell_para_id(cid)
        if cp_match is not None:
            t, r, c, p_sub = cp_match
            tc = cell_idx.get((t, r, c))
            if tc is None:
                continue
            sub = tc.find(f"{{{HP_NS}}}subList")
            if sub is None:
                continue
            ps = sub.findall(f"{{{HP_NS}}}p")
            if p_sub < len(ps) and set_paragraph_text(ps[p_sub], str(text)):
                stats["filled_cellpara"] = stats.get("filled_cellpara", 0) + 1
                filled_tcs.append(tc)
            continue

        p_match = parse_para_id(cid)
        if p_match is not None:
            p_el = para_idx.get(p_match)
            if p_el is not None and set_paragraph_text(p_el, str(text)):
                stats["filled_para"] = stats.get("filled_para", 0) + 1
            continue
        try:
            t, r, c = parse_cell_id(cid)
        except ValueError:
            stats["failed_id"] = stats.get("failed_id", 0) + 1
            continue
        tc = cell_idx.get((t, r, c))
        if tc is None:
            continue
        if operation in ("check", "uncheck"):
            if apply_cell_check(tc, operation):
                stats["filled_check"] = stats.get("filled_check", 0) + 1
                filled_tcs.append(tc)
        else:
            # 가드: standalone 작성요령(1×1 ※ 박스)은 내용으로 채우지 않음 — 양식 안내문 보존
            if _is_standalone_instruction_box(tc):
                stats["blocked_instruction_box"] = stats.get("blocked_instruction_box", 0) + 1
                print(f"  WARN 작성요령 박스 채움 거부: {cid} (1×1 ※ 박스, 안내문 보존)",
                      file=sys.stderr)
                continue
            # 가드: 채울 내용에 *다른 컬럼 헤더* 마커가 들어있으면 mis-mapping 의심 → 거부
            mismap = _detect_column_mismap(tc, str(text))
            if mismap is not None:
                stats["blocked_column_mismap"] = stats.get("blocked_column_mismap", 0) + 1
                print(f"  WARN 컬럼 매핑 오류 채움 거부: {cid} (다른 컬럼 헤더 '{mismap}' 가 내용에 마커로 등장)",
                      file=sys.stderr)
                continue
            if set_cell_text(tc, str(text)):
                stats["filled_cell"] = stats.get("filled_cell", 0) + 1
                filled_tcs.append(tc)

    # 단락 주입을 마지막에, anchor 내림차순으로 (높은 인덱스 삽입이 낮은 anchor 를 안 밀게)
    for anchor_idx, lines in sorted(inject_jobs, key=lambda j: -j[0]):
        n = inject_paragraphs(root, anchor_idx, lines)
        stats["injected_para"] = stats.get("injected_para", 0) + n

    # 모든 fill·inject 완료 후 *잔존 placeholder*(가나다·단독 마커) 자동 정리 — 일반 가드
    n_cleaned = cleanup_residual_placeholders(root)
    if n_cleaned:
        stats["cleaned_residual"] = stats.get("cleaned_residual", 0) + n_cleaned

    # 채운 셀의 row 고정높이 lock 해제 — 표 페이지 초과·빈공간 잔존 방지 (일반 가드)
    n_released = release_cell_height_locks(filled_tcs)
    if n_released:
        stats["released_cell_height"] = stats.get("released_cell_height", 0) + n_released

    body = etree.tostring(root, encoding="unicode")
    header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    section_path.write_bytes((header + body).encode("utf-8"))


def add_green_char_style(header_path: Path) -> int:
    """header.xml에 녹색(#00AA00) 글자 스타일 추가, 새 id 반환.

    *의도된* 기능: AI가 채운 셀·단락 텍스트를 녹색으로 표시해 양식 원본(검정)과
    구분한다 (디버그·검토용). 버그 아님 — 제거하거나 "검정으로 고쳐야 한다"고
    문제삼지 말 것. 발주처 실제 제출 시에만 검정 버전을 별도 생성한다.
    (자세히: .claude/CLAUDE.md "AI가 채운 셀 텍스트는 *녹색*" 절)
    """
    global GREEN_CHAR_PR_ID
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(header_path), parser)
    root = tree.getroot()

    # charProperties 찾기
    char_props = root.find(f".//{{{HH_NS}}}charProperties")
    if char_props is None:
        return None

    # 기존 최대 id 찾기
    max_id = 0
    for cp in char_props.findall(f"{{{HH_NS}}}charPr"):
        cp_id = int(cp.get("id", "0"))
        if cp_id > max_id:
            max_id = cp_id

    new_id = max_id + 1

    # 녹색 charPr 추가 (기존 id=0 스타일 복사 + 색상만 녹색)
    first_cp = char_props.find(f"{{{HH_NS}}}charPr")
    if first_cp is not None:
        new_cp = etree.Element(f"{{{HH_NS}}}charPr")
        new_cp.set("id", str(new_id))
        new_cp.set("height", first_cp.get("height", "1000"))
        new_cp.set("textColor", "#00AA00")  # 녹색
        new_cp.set("shadeColor", first_cp.get("shadeColor", "#FFFFFFFF"))
        new_cp.set("useFontSpace", first_cp.get("useFontSpace", "0"))
        new_cp.set("useKerning", first_cp.get("useKerning", "0"))
        new_cp.set("symMark", first_cp.get("symMark", "NONE"))
        new_cp.set("borderFillIDRef", first_cp.get("borderFillIDRef", "2"))

        # 자식 요소 복사
        for child in first_cp:
            new_child = etree.SubElement(new_cp, child.tag)
            for k, v in child.attrib.items():
                new_child.set(k, v)

        char_props.append(new_cp)

        # itemCnt 업데이트
        char_props.set("itemCnt", str(int(char_props.get("itemCnt", "0")) + 1))

    # 저장
    body = etree.tostring(root, encoding="unicode")
    xml_header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    header_path.write_bytes((xml_header + body).encode("utf-8"))

    GREEN_CHAR_PR_ID = new_id
    return new_id


def fill_hwpx(form_path: str, fills_path: str, out_path: str, project_root: Path = None):
    """HWPX 양식에 fills.yaml 내용 적용.

    Args:
        project_root: 이미지 상대 경로 해석을 위한 프로젝트 루트.
                     None이면 스크립트 부모 폴더 사용.
    """
    global GREEN_CHAR_PR_ID

    if project_root is None:
        project_root = Path(__file__).parent.parent

    _load_fill_config(project_root)  # filler 패턴 등 (단락 주입용)

    fills_data = yaml.safe_load(Path(fills_path).read_text(encoding="utf-8"))
    fills = fills_data.get("fills", [])
    if not fills:
        print("WARN: fills 비어있음", file=sys.stderr)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with zipfile.ZipFile(form_path, "r") as zin:
            zin.extractall(td_path)

        # header.xml에 녹색 글자 스타일 추가
        header_file = td_path / "Contents" / "header.xml"
        if header_file.exists():
            green_id = add_green_char_style(header_file)
            print(f"녹색 글자 스타일 추가: charPrIDRef={green_id}", file=sys.stderr)

        # 1단계: 이미지 삽입 사전 처리
        # - 이미지 파일을 BinData에 복사
        # - content.hpf에 등록
        # - image_registry 구성
        image_registry = {}
        # meta.company 없으면 None → 검색이 kb/company/* 전체를 탐색 (특정 회사 기본값 박지 않음)
        company = fills_data.get("meta", {}).get("company") or None

        for entry in fills:
            operation = entry.get("operation", "")
            if operation not in ("insert_image", "auto_image"):
                continue

            cid = entry.get("id", "")
            if not cid:
                continue

            src_path = None

            if operation == "insert_image":
                # 명시적 이미지 경로
                image_ref = entry.get("image_path", "")
                if not image_ref:
                    continue
                src_path = resolve_image_path(image_ref, project_root)
                if src_path is None:
                    print(f"WARN: 이미지 없음: {image_ref}", file=sys.stderr)
                    continue

            elif operation == "auto_image":
                # KB에서 자동 검색
                context = entry.get("context", "")
                if not context:
                    # hints에서 컨텍스트 추출
                    hints = entry.get("hints", {})
                    context = hints.get("left", "") or hints.get("table_label", "")

                if not context:
                    print(f"WARN: auto_image 컨텍스트 없음: {cid}", file=sys.stderr)
                    continue

                src_path = search_kb_image(context, company=company, project_root=project_root)
                if src_path is None:
                    print(f"WARN: KB에서 이미지 못 찾음: {cid} (컨텍스트: {context[:30]}...)", file=sys.stderr)
                    continue

            if src_path is None:
                continue

            # BinData에 이미지 복사
            image_id, suffix = add_image_to_bindata(td_path, src_path)

            # content.hpf에 등록
            update_content_hpf(td_path, image_id, suffix)

            # 이미지 크기 가져오기
            width_px, height_px = get_image_dimensions(src_path)

            # 레지스트리에 등록
            image_registry[cid] = (image_id, width_px, height_px)
            mode = "자동" if operation == "auto_image" else "명시"
            print(f"이미지 등록({mode}): {cid} → {image_id} ({width_px}x{height_px}px)", file=sys.stderr)

        # 2단계: section XML 편집
        section_dir = td_path / "Contents"
        section_files = sorted(section_dir.glob("section*.xml"))
        if not section_files:
            raise RuntimeError(f"section*.xml 없음: {section_dir}")

        stats = {"filled": 0}
        for sf in section_files:
            fill_section(sf, fills, stats, image_registry)

        # 3단계: ZIP으로 다시 묶기
        out_abs = Path(out_path).resolve()
        if out_abs.exists():
            out_abs.unlink()
        with zipfile.ZipFile(out_abs, "w", zipfile.ZIP_DEFLATED) as zout:
            mime = td_path / "mimetype"
            if mime.exists():
                zout.write(mime, "mimetype", zipfile.ZIP_STORED)
            for f in td_path.rglob("*"):
                if not f.is_file() or f == mime:
                    continue
                arc = f.relative_to(td_path).as_posix()
                zout.write(f, arc)

    # 결과 출력
    img_total = stats.get("filled_image", 0) + stats.get("filled_image_auto", 0)
    parts = [
        f"셀 {stats.get('filled_cell', 0)}",
        f"단락 {stats.get('filled_para', 0)}",
        f"셀안단락 {stats.get('filled_cellpara', 0)}",
        f"주입단락 {stats.get('injected_para', 0)}",
        f"잔존정리 {stats.get('cleaned_residual', 0)}",
        f"높이해제 {stats.get('released_cell_height', 0)}",
        f"체크 {stats.get('filled_check', 0)}",
        f"이미지 {img_total} (명시 {stats.get('filled_image', 0)} + 자동 {stats.get('filled_image_auto', 0)})",
    ]
    print(f"채움: {' + '.join(parts)} / 총 {len(fills)} 명세", file=sys.stderr)
    print(f"저장: {out_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        print("사용: python scripts/fill_hwpx_form.py <form.hwpx> <fills.yaml> <output.hwpx>")
        sys.exit(1)
    fill_hwpx(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
