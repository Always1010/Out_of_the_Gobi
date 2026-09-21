"""Build a local, offline biography HTML from reviewed data and static assets."""
import json
import shutil
from pathlib import Path
from validate_story import validate

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent


def json_script(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def build():
    data = validate()
    chapters = json.loads((ROOT / 'book_reader/text/chapters.json').read_text(encoding='utf8'))
    data['chapters'] = [dict(id=c['id'], title=c['title_simplified'], start=c['pdf_page_start'], section=f'section-{i+1:02d}') for i, c in enumerate(chapters)]
    land = json.loads((BASE / 'assets/ne_110m_land.geojson').read_text(encoding='utf8'))
    html = (BASE / 'src/index.html').read_text(encoding='utf8')
    for marker, value in {
        '/* STYLE */': (BASE / 'src/style.css').read_text(encoding='utf8'),
        '/* DATA */': json_script(data),
        '/* LAND */': json_script(land),
        '/* SCRIPT */': (BASE / 'src/app.js').read_text(encoding='utf8'),
    }.items():
        assert html.count(marker) == 1, marker
        html = html.replace(marker, value)
    dest = BASE / 'dist'
    (dest / 'assets').mkdir(parents=True, exist_ok=True)
    for stage in data['stages']:
        filename = f'page-{stage["photo"]:03d}.jpg'
        shutil.copyfile(ROOT / 'book_reader/images/pages' / filename, dest / 'assets' / filename)
    (dest / 'index.html').write_text(html, encoding='utf8')
    assert '/* DATA */' not in html
    print(f'Built biography/dist/index.html ({len(html.encode("utf8")):,} bytes), {len(data["stages"])} original book plates.')


if __name__ == '__main__':
    build()
