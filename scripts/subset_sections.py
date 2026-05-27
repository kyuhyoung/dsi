"""form.yaml(sections 자동 검출본)에서 라벨에 특정 문자열이 든 섹션만 골라
1-섹션(또는 N) sections yaml 로 출력. 손코딩 범위 없이 *자동 검출* 범위를 그대로 사용.

용법: python scripts/subset_sections.py <form.yaml> <label_substring> <out.yaml>
예:   python scripts/subset_sections.py 통합양식_v3.form.yaml 사업계획서 _sections_본체.yaml
"""
import sys
import yaml

src, needle, out = sys.argv[1], sys.argv[2], sys.argv[3]
data = yaml.safe_load(open(src, encoding="utf-8")) or {}
sections = data.get("sections", [])
picked = [s for s in sections if needle in (s.get("label", "") or s.get("label_full", ""))]
if not picked:
    print("ERR: '{}' 포함 섹션 없음 (sections {}개)".format(needle, len(sections)), file=sys.stderr)
    sys.exit(1)
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump({"sections": picked}, f, allow_unicode=True, sort_keys=False)
for s in picked:
    print("picked: {} range={}".format(s.get("label"), s.get("paragraph_range")), file=sys.stderr)
print("saved {} ({} section)".format(out, len(picked)), file=sys.stderr)
