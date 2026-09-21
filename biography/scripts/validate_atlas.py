"""Validate the editorial map, evidence, and fixed diagram geometry."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent


def validate_atlas(story=None):
    data = json.loads((BASE / 'data/atlas.json').read_text(encoding='utf8'))
    story = story or json.loads((BASE / 'data/story.json').read_text(encoding='utf8'))
    nodes = {n['id']: n for n in data['nodes']}
    sources = {s['id']: s for s in data['sources']}
    events = {e['id']: e for e in story['events']}
    people = {p['id'] for p in story['people']}
    errors = []
    assert len(nodes) == len(data['nodes']), 'Duplicate node ids'
    assert len(sources) == len(data['sources']), 'Duplicate source ids'
    pages = {}
    for p in (ROOT / 'book_reader/text/simplified').glob('*.md'):
        chapter = re.sub(r'^\d+-', '', p.stem)
        parts = re.split(r'<!-- PDF (\d+) -->', p.read_text(encoding='utf8'))
        for i in range(1, len(parts), 2):
            pages[chapter, int(parts[i])] = parts[i+1]
    norm = lambda t: re.sub(r'\s+', '', t)
    quotes = 0
    for n in data['nodes']:
        prefix = n['id']
        if not n['paragraphs']:
            errors.append(f'{prefix}: empty narrative')
        if not (n.get('source_refs') or n.get('events') or n.get('source_ids')):
            errors.append(f'{prefix}: no evidence')
        for field, index in [('events', events), ('people', people), ('related', nodes), ('source_ids', sources)]:
            for key in n.get(field, []):
                if key not in index:
                    errors.append(f'{prefix}: missing {field}/{key}')
        for ref in n.get('source_refs', []):
            for page in ref['pdf_pages']:
                if (ref['chapter_id'], page) not in pages:
                    errors.append(f'{prefix}: missing source page {ref}/{page}')
        if n.get('quote'):
            q = n['quote']
            actual = pages.get((n['chapter_id'], q['pdf_page']), '')
            if norm(q['text']) not in norm(actual):
                errors.append(f'{prefix}: quote mismatch PDF {q["pdf_page"]}')
            quotes += 1
    assert len(data['clusters']) == 8
    assert len(data['extension_map']) == 5
    visible = []
    for c in data['clusters']:
        visible += [c['hub'], c['history']['id']] + [b['id'] for b in c['branches']]
        assert 150 <= c['x'] <= 1260 and c['y'] in (165, 590)
        assert len(c['branches']) == 2
    for c in data['extension_map']:
        visible += [c['hub']] + [b['id'] for b in c['branches']]
    assert len(visible) == len(set(visible)), 'Map nodes must have unique positions'
    for id in visible:
        assert id in nodes, id
    for r in data['relations']:
        assert len(r['nodes']) >= 2
        assert all(id in nodes for id in r['nodes'])
    for s in sources.values():
        assert s['url'].startswith('https://'), s['id']
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Validated {len(nodes)} map narratives, {len(visible)} visible nodes, {quotes} exact book quotes, {len(sources)} web sources.')
    return data


if __name__ == '__main__':
    validate_atlas()
