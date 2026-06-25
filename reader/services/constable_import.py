import re
import logging
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.db import transaction
from ..models import ExternalNote

logger = logging.getLogger(__name__)

BASE_URL = 'https://soniclight.com/tcon/notes/html'

BOOK_SLUGS = {
    'Genesis': 'genesis',
    'Exodus': 'exodus',
    'Leviticus': 'leviticus',
    'Numbers': 'numbers',
    'Deuteronomy': 'deuteronomy',
    'Joshua': 'joshua',
    'Judges': 'judges',
    'Ruth': 'ruth',
    '1 Samuel': '1samuel',
    '2 Samuel': '2samuel',
    '1 Kings': '1kings',
    '2 Kings': '2kings',
    '1 Chronicles': '1chronicles',
    '2 Chronicles': '2chronicles',
    'Ezra': 'ezra',
    'Nehemiah': 'nehemiah',
    'Esther': 'esther',
    'Job': 'job',
    'Psalms': 'psalms',
    'Proverbs': 'proverbs',
    'Ecclesiastes': 'ecclesiastes',
    'Song of Solomon': 'song',
    'Isaiah': 'isaiah',
    'Jeremiah': 'jeremiah',
    'Lamentations': 'lamentations',
    'Ezekiel': 'ezekiel',
    'Daniel': 'daniel',
    'Hosea': 'hosea',
    'Joel': 'joel',
    'Amos': 'amos',
    'Obadiah': 'obadiah',
    'Jonah': 'jonah',
    'Micah': 'micah',
    'Nahum': 'nahum',
    'Habakkuk': 'habakkuk',
    'Zephaniah': 'zephaniah',
    'Haggai': 'haggai',
    'Zechariah': 'zechariah',
    'Malachi': 'malachi',
    'Matthew': 'matthew',
    'Mark': 'mark',
    'Luke': 'luke',
    'John': 'john',
    'Acts': 'acts',
    'Romans': 'romans',
    '1 Corinthians': '1corinthians',
    '2 Corinthians': '2corinthians',
    'Galatians': 'galatians',
    'Ephesians': 'ephesians',
    'Philippians': 'philippians',
    'Colossians': 'colossians',
    '1 Thessalonians': '1thessalonians',
    '2 Thessalonians': '2thessalonians',
    '1 Timothy': '1timothy',
    '2 Timothy': '2timothy',
    'Titus': 'titus',
    'Philemon': 'philemon',
    'Hebrews': 'hebrews',
    'James': 'james',
    '1 Peter': '1peter',
    '2 Peter': '2peter',
    '1 John': '1john',
    '2 John': '2john',
    '3 John': '3john',
    'Jude': 'jude',
    'Revelation': 'revelation',
}

VERSE_REF_RE = re.compile(r'(\d+):(\d+)(?:\s*[-\u2013\u2014]\s*(?:(\d+):)?(\d+))?')

SINGLE_CHAPTER_VERSE_RE = re.compile(r'(?:V[Vv]?\.\s+)?(\d+)(?:\s*[-\u2013\u2014]\s*(\d+))?\s*$')

SINGLE_CHAPTER_BOOKS = {'Obadiah', 'Philemon', '2 John', '3 John', 'Jude'}

HEADING_TAGS = ['h2', 'h3', 'h4', 'h5', 'h6']


class ConstableImportService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BibleTeacher/1.0 (Constable Notes Import)'
        })

    def _build_url(self, book_name):
        slug = BOOK_SLUGS.get(book_name)
        if not slug:
            raise ValueError(f"Unknown book: {book_name}")
        return f"{BASE_URL}/{slug}/{slug}.htm"

    def _fetch_html(self, url):
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
                resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def _parse_verse_ref(self, heading_text, book_name=None):
        matches = list(VERSE_REF_RE.finditer(heading_text))
        if matches:
            last = matches[-1]
            chapter = int(last.group(1))
            verse_start = int(last.group(2))
            verse_end = int(last.group(4)) if last.group(4) else None
            return chapter, verse_start, verse_end

        if book_name in SINGLE_CHAPTER_BOOKS:
            m = SINGLE_CHAPTER_VERSE_RE.search(heading_text)
            if m:
                verse_start = int(m.group(1))
                verse_end = int(m.group(2)) if m.group(2) else None
                return 1, verse_start, verse_end

        return None

    def _extract_exposition_section(self, soup):
        exp_heading = soup.find('h2', string=lambda t: t and 'Exposition' in t.strip())
        if not exp_heading:
            return []
        siblings = []
        for sib in exp_heading.next_siblings:
            if isinstance(sib, Tag) and sib.name == 'h2':
                break
            siblings.append(sib)
        return siblings

    def _collect_paragraphs(self, siblings, start_index):
        paragraphs = []
        i = start_index
        while i < len(siblings):
            el = siblings[i]
            if isinstance(el, Tag) and el.name in HEADING_TAGS:
                break
            if isinstance(el, Tag) and el.name == 'p':
                paragraphs.append(str(el))
            elif isinstance(el, NavigableString) and str(el).strip():
                paragraphs.append(f'<p>{str(el).strip()}</p>')
            i += 1
        return paragraphs, i

    def parse_html(self, html_content, book_name):
        soup = BeautifulSoup(html_content, 'lxml')
        siblings = self._extract_exposition_section(soup)
        if not siblings:
            logger.warning(f"No Exposition section found for {book_name}")
            return []

        notes = []
        i = 0
        while i < len(siblings):
            el = siblings[i]
            if isinstance(el, Tag) and el.name in HEADING_TAGS:
                heading_text = el.get_text(strip=True)
                ref = self._parse_verse_ref(heading_text, book_name)
                if ref:
                    chapter, verse_start, verse_end = ref
                    paragraphs, next_i = self._collect_paragraphs(siblings, i + 1)
                    if paragraphs:
                        note_text = '\n'.join(paragraphs)
                        notes.append({
                            'source': 'constable',
                            'book': book_name,
                            'chapter': chapter,
                            'verse_start': verse_start,
                            'verse_end': verse_end,
                            'note_text': note_text,
                        })
                    i = next_i
                    continue
            i += 1

        return notes

    @transaction.atomic
    def _save_notes(self, notes, overwrite=False):
        created = 0
        updated = 0
        for note_data in notes:
            lookup = {
                'source': note_data['source'],
                'book': note_data['book'],
                'chapter': note_data['chapter'],
                'verse_start': note_data['verse_start'],
                'verse_end': note_data['verse_end'],
            }
            defaults = {
                'note_text': note_data['note_text'],
            }
            if overwrite:
                _, created_flag = ExternalNote.objects.update_or_create(
                    **lookup,
                    defaults=defaults,
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            else:
                _, created_flag = ExternalNote.objects.get_or_create(
                    **lookup,
                    defaults=defaults,
                )
                if created_flag:
                    created += 1
        return created, updated

    def import_book(self, book_name, overwrite=False):
        url = self._build_url(book_name)
        logger.info(f"Fetching {book_name} from {url}")
        html = self._fetch_html(url)
        notes = self.parse_html(html, book_name)
        logger.info(f"Parsed {len(notes)} notes for {book_name}")
        created, updated = self._save_notes(notes, overwrite=overwrite)
        logger.info(f"{book_name}: {created} created, {updated} updated")
        return {
            'book': book_name,
            'url': url,
            'parsed': len(notes),
            'created': created,
            'updated': updated,
        }

    def import_all(self, overwrite=False, book_names=None):
        names = book_names or list(BOOK_SLUGS.keys())
        results = []
        for name in names:
            try:
                result = self.import_book(name, overwrite=overwrite)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to import {name}: {e}")
                results.append({
                    'book': name,
                    'error': str(e),
                    'parsed': 0,
                    'created': 0,
                    'updated': 0,
                })
        return results
