"""Embed graph data in offline HTML; page previews remain adjacent assets."""
import json
from pathlib import Path

base = Path(__file__).resolve().parent
graph = json.loads((base / 'data' / 'graph.json').read_text(encoding='utf-8'))
template = (base / 'site' / 'index.template.html').read_text(encoding='utf-8')
payload = json.dumps(graph, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
out = base / 'site' / 'index.html'
out.write_text(template.replace('__GRAPH_JSON__', payload), encoding='utf-8')
print(out, out.stat().st_size, 'bytes')
