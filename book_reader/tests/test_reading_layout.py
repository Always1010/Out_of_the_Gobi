"""Scan-reviewed reading semantics must not depend on generic paragraph guesses."""
import json
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_common import (TEXT, BOOK, Block, apply_verse_layout, chapter_number,
    load_chapters, load_frontmatter, load_captions, parse_blocks, reading_layout, with_lead_ins)

class FrontmatterTests(unittest.TestCase):
    def test_author_is_seven_real_paragraphs_and_dedication_stays_scan(self):
        for script in ('traditional', 'simplified'):
            front = load_frontmatter(script)
            self.assertEqual([f.presentation for f in front], ['text', 'scan'])
            self.assertEqual(len(front[0].blocks), 7)
            self.assertTrue(all(b.kind == 'paragraph' for b in front[0].blocks))
            self.assertEqual([f.source_page for f in front], [4,5])

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

class PictureTests(unittest.TestCase):
    def test_reading_crop_preserves_original_source_and_all_captions(self):
        data = reading_layout()
        self.assertEqual(list(data['crops']), ['page-009.jpg'])
        self.assertEqual(data['crops']['page-009.jpg']['box'], [1004,302,1371,767])
        raw = json.loads((BOOK/'images/captions.json').read_text())['pages']
        actual = load_captions('traditional')
        self.assertEqual(sorted(x for v in raw.values() for x in v), sorted(x for v in actual.values() for x in v))
        self.assertEqual(len(actual[164]), 1)
        self.assertEqual(len(actual[165]), 2)
    def test_twenty_unique_body_plates(self):
        for script in ('traditional', 'simplified'):
            plates = [b.value for c in load_chapters(script) for b in c.blocks if b.kind == 'image']
            self.assertEqual(len(plates), 20)
            self.assertEqual(len(set(plates)), 20)

class ChapterStylesTests(unittest.TestCase):
    def test_chapter_numbers_do_not_number_prefaces(self):
        self.assertEqual([chapter_number(i) for i in (1,10,11,20,29)], ['第一章','第十章','第十一章','第二十章','第二十九章'])
        for script in ('traditional', 'simplified'):
            chapters=load_chapters(script)
            self.assertEqual([c.number for c in chapters if c.number], list(range(1,30)))
            self.assertTrue(all(c.label == c.title for c in chapters if not c.number))
    def test_leadins_are_explicit_thirty_sections_thirty_seven_source_paragraphs(self):
        entries=json.loads((TEXT/'lead-ins.json').read_text())['sections']
        self.assertEqual(len(entries),30)
        for script in ('traditional','simplified'):
            self.assertEqual(sum(e['scripts'][script]['paragraph_count'] for e in entries),37)
            self.assertFalse(any(e['id'] in {'foreword','preface','afterword'} for e in entries))
            self.assertEqual(sum(b.kind=='verse' and b.role=='lead-in' for c in load_chapters(script) for b in c.blocks),1)
    def test_unknown_leadin_does_not_guess_first_paragraph(self):
        blocks=(Block('paragraph','第一段'),Block('break','★★★'),Block('paragraph','正文'))
        self.assertEqual(with_lead_ins(blocks,'foreword','simplified'),blocks)

class VerseTests(unittest.TestCase):
    def test_all_eleven_blocks_eighty_one_lines_preserve_source_characters(self):
        manifest=json.loads((TEXT/'chapters.json').read_text())
        for script in ('traditional','simplified'):
            chapters=load_chapters(script)
            verses=[b for c in chapters for b in c.blocks if b.kind=='verse']
            self.assertEqual(len(verses),11)
            self.assertEqual(sum(len(b.value.splitlines()) for b in verses),81)
            self.assertTrue(all(b.alignment=='left' for b in verses))
            for index,(entry,chapter) in enumerate(zip(manifest,chapters),1):
                old=parse_blocks((TEXT/f'{script}-continuous/{index:02d}-{chapter.slug}.md').read_text(),chapter.title)
                compact=lambda bs: re.sub(r'\s+','',''.join(b.value for b in bs))
                self.assertEqual(compact(old),compact(chapter.blocks))
    def test_long_song_combines_original_page_break(self):
        c=next(c for c in load_chapters('simplified') if c.slug=='chapter-09')
        v=next(b for b in c.blocks if b.kind=='verse')
        self.assertEqual(len(v.value.splitlines()),26)
        self.assertNotIn('\n\n',v.value)
        self.assertEqual(v.value.splitlines()[2],'我的家乡。')
    def test_exact_range_can_split_a_leadin_and_join_adjacent_paragraphs(self):
        rule={'id':'test','chapter':'chapter','alignment':'left','lines_simplified':['诗一，','诗二。']}
        b=(Block('paragraph','前文。诗一，','lead-in'),Block('paragraph','诗二。后文。','lead-in'))
        actual=apply_verse_layout(b,[rule],'chapter','simplified')
        self.assertEqual(actual,(Block('paragraph','前文。','lead-in'),Block('verse','诗一，\n诗二。','lead-in'),Block('paragraph','后文。','lead-in')))
    def test_mismatches_ambiguity_and_semantic_crossings_fail_closed(self):
        rule={'id':'test','chapter':'chapter','alignment':'left','lines_simplified':['甲乙']}
        for blocks in [(Block('paragraph','甲丙'),),(Block('paragraph','甲乙甲乙'),),(Block('paragraph','甲'),Block('image','page-001.jpg'),Block('paragraph','乙'))]:
            with self.assertRaises(ValueError):apply_verse_layout(blocks,[rule],'chapter','simplified')
    def test_unlisted_ordinary_quotation_is_unchanged(self):
        blocks=(Block('paragraph','普通引文「诗句」。'),)
        self.assertEqual(apply_verse_layout(blocks,[],'chapter','simplified'),blocks)

if __name__ == '__main__': unittest.main()
