"""Scan-reviewed reading semantics must not depend on generic paragraph guesses."""
import json
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_common import (TEXT, BOOK, Block, load_chapters, load_frontmatter)

class PrefaceTests(unittest.TestCase):
    def test_portrait_follows_complete_preface_in_both_scripts(self):
        for script in ('traditional', 'simplified'):
            preface = next(c for c in load_chapters(script) if c.slug == 'preface')
            self.assertEqual(preface.blocks[-1], Block('image', 'page-011.jpg'))
            self.assertIn('2020年3月26日', preface.blocks[-2].value)
            self.assertEqual(sum(b.kind == 'image' for b in preface.blocks), 1)
            phrase = '中英文讀者的文化背景不同' if script == 'traditional' else '中英文读者的文化背景不同'
            self.assertTrue(any(phrase in b.value for b in preface.blocks))
            paginated = (TEXT / script / '02-preface.md').read_text()
            self.assertLess(paginated.index('page-011.jpg'), paginated.index('<!-- PDF 12 -->'))

if __name__ == '__main__': unittest.main()
