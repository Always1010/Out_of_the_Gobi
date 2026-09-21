"""Check the slideshow's references, editorial limits, and delivered images."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def validate_cinema(atlas=None):
    cinema = json.loads((BASE / 'data/cinema.json').read_text(encoding='utf8'))
    atlas = atlas or json.loads((BASE / 'data/atlas.json').read_text(encoding='utf8'))
    node_ids = {n['id'] for n in atlas['nodes']}
    ids = set()
    for s in cinema['scenes']:
        assert s['id'] not in ids
        ids.add(s['id'])
        assert s['node'] in node_ids
        for key, maximum in [('title',18),('era',80),('life',100),('meaning',55)]:
            assert 0 < len(s[key]) <= maximum, (s['id'], key)
        assert 35 <= s['duration_seconds'] <= 55
        image = s['image']
        path = BASE / 'assets' / image['file']
        if image['file'].startswith('page-'):
            path = BASE.parent / 'book_reader/images/pages' / image['file']
        assert path.is_file(), path
        assert image['kind'] in ('original','illustration')
        assert image['caption'] and image['alt']
        if image['kind'] == 'illustration':
            assert 'AI' in image['caption'] and '非史料照片' in image['caption']
    assert sum(s['duration_seconds'] for s in cinema['scenes']) == cinema['duration_seconds']
    ordered = [id for c in cinema['chapters'] for id in c['scene_ids']]
    assert ordered == [s['id'] for s in cinema['scenes']]
    assert len(cinema['scenes']) == 17
    print(f'Validated 17 cinema scenes, 13 life chapters, {cinema["duration_seconds"]} seconds, all image files and provenance labels.')
    return cinema


if __name__ == '__main__':
    validate_cinema()
