"""Check that every guided step has a source and a navigable context."""
import json
from pathlib import Path
from urllib.parse import urlparse
from validate_story import validate

BASE = Path(__file__).resolve().parents[1]


def validate_guide(story=None):
    story = story or validate()
    guide = json.loads((BASE / 'data/guide.json').read_text(encoding='utf8'))
    steps = guide['steps']
    assert len({s['id'] for s in steps}) == len(steps), 'Duplicate guide step'
    sources = {s['id']: s for s in guide['sources']}
    places = {p['id'] for p in story['places'] + guide['places']}
    events = {e['id'] for e in story['events']}
    people = {p['id'] for p in story['people']}
    stages = {s['id'] for s in story['stages']}
    assigned = set()
    for step in steps:
        assert step['title'] and len(step['paragraphs']) >= 2 and step['takeaway'] and step['bridge'], step['id']
        assert set(step['events']) <= events, step['id']
        assert set(step['people']) <= people, step['id']
        assert set(step['route'] + step['stops']) <= places, step['id']
        assert step['stage'] is None or step['stage'] in stages, step['id']
        assert step['photo'] is None or step['photo'] in stages, step['id']
        assert set(step['source_ids']) <= set(sources), step['id']
        if step['part'] == 'extension':
            assert step['source_ids'] and not step['events'], step['id']
        else:
            assert step['events'], step['id']
        assigned.update(step['events'])
    assert assigned == events, 'An original scene was lost from supplementary reading'
    parts = [s['part'] for s in steps]
    assert parts[0] == 'orientation' and parts[-1] == 'reflection'
    assert max(i for i, p in enumerate(parts) if p == 'book') < min(i for i, p in enumerate(parts) if p == 'extension')
    for source in sources.values():
        assert urlparse(source['url']).scheme == 'https' and source['supports'] and source['accessed_at'], source['id']
    for asset in guide.get('images', []):
        assert (BASE / 'assets' / asset['file']).is_file(), asset['id']
        assert asset['source_url'].startswith('https://'), asset['id']
    print(f'Validated {len(steps)} guided steps, coverage of all {len(events)} book scenes, and {len(sources)} source records.')
    return guide


if __name__ == '__main__':
    validate_guide()
