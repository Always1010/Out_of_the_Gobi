"""Validate the curated narrative against the book's page-marked transcription."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'biography/data/story.json'


def validate():
    data = json.loads(DATA.read_text(encoding='utf8'))
    errors = []
    indices = {}
    for kind in ('stages', 'events', 'people', 'places', 'threads'):
        items = data[kind]
        indices[kind] = {item['id']: item for item in items}
        if len(indices[kind]) != len(items):
            errors.append(f'Duplicate IDs: {kind}')
    pages = {}
    for path in (ROOT / 'book_reader/text/simplified').glob('*.md'):
        chapter = re.search(r'(chapter-\d+|afterword)', path.stem)
        if not chapter:
            continue
        chunks = re.split(r'<!-- PDF (\d+) -->', path.read_text(encoding='utf8'))
        for offset in range(1, len(chunks), 2):
            pages[(chapter[0], int(chunks[offset]))] = chunks[offset + 1]
    normalized = lambda text: re.sub(r'\s+', '', text)
    for event in data['events']:
        eid = event['id']
        quote = event['quote']
        source = pages.get((event['chapter_id'], quote['pdf_page']), '')
        if normalized(quote['text']) not in normalized(source):
            errors.append(f'Quote mismatch: {eid}, PDF {quote["pdf_page"]}')
        if quote['pdf_page'] not in event['pdf_pages']:
            errors.append(f'Quote page missing from evidence pages: {eid}')
        for page in event['pdf_pages']:
            if not any(source_page == page for _, source_page in pages):
                errors.append(f'Missing source page: {eid}, {page}')
        for field, kind in (('stage', 'stages'), ('map_place', 'places')):
            if event[field] not in indices[kind]:
                errors.append(f'Missing {field}: {eid}')
        for field, kind in (('person_ids', 'people'), ('tags', 'threads')):
            for value in event[field]:
                if value not in indices[kind]:
                    errors.append(f'Missing {field}: {eid}/{value}')
    ordered = []
    for stage in data['stages']:
        ordered += stage['scenes']
        for eid in stage['scenes']:
            if eid not in indices['events'] or indices['events'][eid]['stage'] != stage['id']:
                errors.append(f'Stage/scene mismatch: {stage["id"]}/{eid}')
        for pid in stage['stops'] + stage['route']:
            if pid not in indices['places']:
                errors.append(f'Missing geographic reference: {pid}')
        if not (ROOT / f'book_reader/images/pages/page-{stage["photo"]:03d}.jpg').is_file():
            errors.append(f'Missing book plate: {stage["photo"]}')
    if len(ordered) != len(set(ordered)) or set(ordered) != set(indices['events']):
        errors.append('Scene assignment must cover each scene exactly once')
    for person in data['people']:
        for eid in person['events']:
            if eid not in indices['events'] or person['id'] not in indices['events'][eid]['person_ids']:
                errors.append(f'Person/scene mismatch: {person["id"]}/{eid}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Validated {len(data["events"])} quotations, scene references, people and source plates.')
    return data


if __name__ == '__main__':
    validate()
