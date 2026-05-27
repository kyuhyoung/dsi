#!/usr/bin/env python3
"""문서(PPT/DOCX/HWPX/PDF)에서 이미지 추출 → KB 이미지 폴더로.

일반화 원칙:
    - 특정 문서/회사에 하드코딩 없음
    - 임의의 회사 KB에서 동작
    - 추출된 이미지는 kb/company/{company}/images/extracted/ 에 저장

용법:
    python scripts/extract_images_from_docs.py <source_dir_or_file> <company> [--min-size 10000]

예:
    python scripts/extract_images_from_docs.py templates/ dabeeo
    python scripts/extract_images_from_docs.py "templates/회사소개.pptx" dabeeo
"""
import sys
import re
import zipfile
import hashlib
from pathlib import Path
from typing import Generator

# Optional imports
try:
    import fitz  # PyMuPDF for PDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


_A_T_RE = re.compile(r'<a:t>(.*?)</a:t>', re.S)
_EMBED_RE = re.compile(r'(?:r:embed|r:link)="(rId\d+)"')
_REL_MEDIA_RE = re.compile(r'Id="(rId\d+)"[^>]*Target="[^"]*?media/([^"]+)"')


def _pptx_media_context(z: zipfile.ZipFile) -> dict:
    """media 파일명 → 그 이미지를 참조하는 슬라이드들의 텍스트(합집합).

    일반화: 특정 deck 구조 가정 없음. slide XML 의 <a:t> 텍스트와
    slide rels 의 media 참조만 사용 (임의 pptx 에서 동작).
    """
    names = z.namelist()
    slide_re = re.compile(r'ppt/slides/slide\d+\.xml$')
    media_ctx = {}
    for name in names:
        if not slide_re.match(name):
            continue
        try:
            sx = z.read(name).decode('utf-8', 'ignore')
        except Exception:
            continue
        texts = [t.strip() for t in _A_T_RE.findall(sx) if t.strip()]
        joined = ' '.join(texts)
        embeds = _EMBED_RE.findall(sx)
        if not embeds:
            continue
        rels_name = name.replace('slides/', 'slides/_rels/') + '.rels'
        rid_to_media = {}
        if rels_name in names:
            rels_xml = z.read(rels_name).decode('utf-8', 'ignore')
            for rid, media in _REL_MEDIA_RE.findall(rels_xml):
                rid_to_media[rid] = media
        for rid in embeds:
            media = rid_to_media.get(rid)
            if media:
                media_ctx.setdefault(media, []).append(joined)
    # 합집합 텍스트로 정리
    return {m: ' '.join(dict.fromkeys(txts)) for m, txts in media_ctx.items()}


def extract_from_pptx(pptx_path: Path) -> Generator[tuple, None, None]:
    """PPTX에서 이미지 추출 + 출처 슬라이드 텍스트(context) 동반.

    yield: (data, ext, prefix, context_text)
    """
    try:
        with zipfile.ZipFile(pptx_path, 'r') as z:
            media_ctx = _pptx_media_context(z)
            for name in z.namelist():
                if name.startswith('ppt/media/') and not name.endswith('/'):
                    data = z.read(name)
                    ext = Path(name).suffix.lower()
                    media_file = Path(name).name
                    context = media_ctx.get(media_file, "")
                    yield (data, ext, f"pptx_{Path(name).stem}", context)
    except Exception as e:
        print(f"  WARN: PPTX 추출 실패 {pptx_path}: {e}", file=sys.stderr)


def extract_from_docx(docx_path: Path) -> Generator[tuple, None, None]:
    """DOCX에서 이미지 추출. (media 폴더)"""
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/') and not name.endswith('/'):
                    data = z.read(name)
                    ext = Path(name).suffix.lower()
                    yield (data, ext, f"docx_{Path(name).stem}", "")
    except Exception as e:
        print(f"  WARN: DOCX 추출 실패 {docx_path}: {e}", file=sys.stderr)


def extract_from_hwpx(hwpx_path: Path) -> Generator[tuple, None, None]:
    """HWPX에서 이미지 추출. (BinData 폴더)"""
    try:
        with zipfile.ZipFile(hwpx_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('BinData/') and not name.endswith('/'):
                    data = z.read(name)
                    ext = Path(name).suffix.lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.emf', '.wmf']:
                        yield (data, ext, f"hwpx_{Path(name).stem}", "")
    except Exception as e:
        print(f"  WARN: HWPX 추출 실패 {hwpx_path}: {e}", file=sys.stderr)


def extract_from_pdf(pdf_path: Path) -> Generator[tuple, None, None]:
    """PDF에서 이미지 추출. (PyMuPDF 필요)"""
    if not HAS_FITZ:
        print(f"  SKIP: PDF 추출 불가 (pip install PyMuPDF 필요)", file=sys.stderr)
        return

    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()
            for img_idx, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                data = base_image["image"]
                ext = f".{base_image['ext']}"
                yield (data, ext, f"pdf_p{page_num+1}_img{img_idx+1}", "")
        doc.close()
    except Exception as e:
        print(f"  WARN: PDF 추출 실패 {pdf_path}: {e}", file=sys.stderr)


def extract_images(doc_path: Path, min_size: int = 10000) -> list:
    """문서에서 이미지 추출. 확장자에 따라 적절한 추출기 선택."""
    suffix = doc_path.suffix.lower()

    extractors = {
        '.pptx': extract_from_pptx,
        '.docx': extract_from_docx,
        '.hwpx': extract_from_hwpx,
        '.pdf': extract_from_pdf,
    }

    extractor = extractors.get(suffix)
    if extractor is None:
        return []

    results = []
    for data, ext, prefix, context in extractor(doc_path):
        if len(data) >= min_size:
            # 해시로 중복 방지
            hash_suffix = hashlib.md5(data).hexdigest()[:8]
            filename = f"{prefix}_{hash_suffix}{ext}"
            results.append((data, filename, context))

    return results


def scan_and_extract(source: Path, company: str, project_root: Path, min_size: int = 10000):
    """소스 경로에서 문서를 찾아 이미지 추출."""
    output_dir = project_root / "kb" / "company" / company / "images" / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_extensions = {'.pptx', '.docx', '.hwpx', '.pdf'}

    # 파일 또는 디렉토리
    if source.is_file():
        docs = [source] if source.suffix.lower() in doc_extensions else []
    else:
        docs = [f for f in source.rglob('*') if f.suffix.lower() in doc_extensions]

    total_extracted = 0
    seen_hashes = set()
    index_entries = []

    for doc in docs:
        print(f"처리 중: {doc.name}", file=sys.stderr)
        images = extract_images(doc, min_size)

        for data, filename, context in images:
            # 중복 체크
            data_hash = hashlib.md5(data).hexdigest()
            if data_hash in seen_hashes:
                continue
            seen_hashes.add(data_hash)

            # 저장
            out_path = output_dir / filename
            out_path.write_bytes(data)
            index_entries.append({
                "file": filename,
                "source": doc.name,
                "context_text": (context or "").strip()[:600],
            })
            print(f"  추출: {filename} ({len(data):,} bytes)")
            total_extracted += 1

    # index.yaml — 추출 이미지 ↔ 출처 텍스트 (auto_image 검색이 키워드 매칭에 사용)
    # 일반화: 특정 회사/이미지 하드코딩 없음. 문서 자체 텍스트만 기록.
    write_index(output_dir, index_entries)

    print(f"\n총 {total_extracted}개 이미지 추출 → {output_dir}", file=sys.stderr)
    print(f"index.yaml: {len(index_entries)}개 항목", file=sys.stderr)
    return total_extracted


def write_index(output_dir: Path, entries: list):
    """추출 이미지 색인을 index.yaml 로 저장."""
    try:
        import yaml
        index_path = output_dir / "index.yaml"
        with open(index_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"images": entries}, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"  WARN: index.yaml 저장 실패: {e}", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print("사용: python scripts/extract_images_from_docs.py <source> <company> [--min-size N]")
        print("예: python scripts/extract_images_from_docs.py templates/ dabeeo")
        sys.exit(1)

    source = Path(sys.argv[1])
    company = sys.argv[2]
    min_size = 10000  # 기본 10KB 이상

    # --min-size 옵션
    if '--min-size' in sys.argv:
        idx = sys.argv.index('--min-size')
        if idx + 1 < len(sys.argv):
            min_size = int(sys.argv[idx + 1])

    project_root = Path(__file__).parent.parent

    if not source.exists():
        print(f"ERR: 소스 없음: {source}", file=sys.stderr)
        sys.exit(1)

    scan_and_extract(source, company, project_root, min_size)


if __name__ == "__main__":
    main()
