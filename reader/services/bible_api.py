import requests
import bleach
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

ALLOWED_HTML_TAGS = [
    'p', 'span', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 'sup', 'sub', 'a', 'ul', 'ol', 'li',
    'blockquote', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
]

ALLOWED_HTML_ATTRS = {
    'a': ['href', 'title'],
    'span': ['class', 'data-verse-id', 'data-verse-number'],
    'div': ['class'],
    'p': ['class'],
    'sup': ['class'],
    'sub': ['class'],
}

BIBLE_BOOKS = [
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
    'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel',
    '1 Kings', '2 Kings', '1 Chronicles', '2 Chronicles', 'Ezra',
    'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs',
    'Ecclesiastes', 'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations',
    'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
    'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk',
    'Zephaniah', 'Haggai', 'Zechariah', 'Malachi', 'Matthew',
    'Mark', 'Luke', 'John', 'Acts', 'Romans',
    '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians', 'Philippians',
    'Colossians', '1 Thessalonians', '2 Thessalonians', '1 Timothy', '2 Timothy',
    'Titus', 'Philemon', 'Hebrews', 'James', '1 Peter',
    '2 Peter', '1 John', '2 John', '3 John', 'Jude',
    'Revelation',
]

BIBLE_BOOK_CHAPTERS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, 'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36, 'Ezra': 10,
    'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalms': 150, 'Proverbs': 31,
    'Ecclesiastes': 12, 'Song of Solomon': 8, 'Isaiah': 66, 'Jeremiah': 52, 'Lamentations': 5,
    'Ezekiel': 48, 'Daniel': 12, 'Hosea': 14, 'Joel': 3, 'Amos': 9,
    'Obadiah': 1, 'Jonah': 4, 'Micah': 7, 'Nahum': 3, 'Habakkuk': 3,
    'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4, 'Matthew': 28,
    'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28, 'Romans': 16,
    '1 Corinthians': 16, '2 Corinthians': 13, 'Galatians': 6, 'Ephesians': 6, 'Philippians': 4,
    'Colossians': 4, '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6, '2 Timothy': 4,
    'Titus': 3, 'Philemon': 1, 'Hebrews': 13, 'James': 5, '1 Peter': 5,
    '2 Peter': 3, '1 John': 5, '2 John': 1, '3 John': 1, 'Jude': 1,
    'Revelation': 22,
}

# Psalm 119 is the longest chapter (176 verses); used as a safe fallback when the external API is unavailable
MAX_VERSE_FALLBACK = 176


def sanitize_html(html_content):
    if not html_content or not isinstance(html_content, str):
        return html_content
    return bleach.clean(
        html_content,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRS,
        strip=True
    )


class BibleAPIService:
    BASE_URL = 'https://api.scripture.api.bible/v1'
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'BIBLE_API_KEY', None)
        if not self.api_key:
            raise ValueError("Bible API key not configured. Set BIBLE_API_KEY in settings.")
        self.headers = {
            'api-key': self.api_key
        }
        self.default_version = getattr(settings, 'DEFAULT_BIBLE_VERSION', 'de4e12af7f28f599-02')
    
    def _make_request(self, endpoint, params=None):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Bible API request failed: {e}")
            return None
    
    def get_available_versions(self):
        cache_key = 'bible_versions'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request('bibles', params={'language': 'eng'})
        if data and 'data' in data:
            versions = data['data']
            seen_names = set()
            unique_versions = []
            for v in versions:
                display_name = v.get('nameLocal') or v.get('name') or ''
                if display_name and display_name not in seen_names:
                    seen_names.add(display_name)
                    unique_versions.append(v)
            cache.set(cache_key, unique_versions, 86400)
            return unique_versions
        return []
    
    def get_books(self, version_id=None):
        version_id = version_id or self.default_version
        cache_key = f'bible_books_{version_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f'bibles/{version_id}/books')
        if data and 'data' in data:
            books = data['data']
            cache.set(cache_key, books, 86400)
            return books
        return []
    
    def get_chapters(self, book_id, version_id=None):
        version_id = version_id or self.default_version
        cache_key = f'bible_chapters_{version_id}_{book_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request(f'bibles/{version_id}/books/{book_id}/chapters')
        if data and 'data' in data:
            chapters = data['data']
            cache.set(cache_key, chapters, 86400)
            return chapters
        return []
    
    def get_chapter(self, book_id, chapter_number, version_id=None, include_notes=False):
        version_id = version_id or self.default_version
        cache_key = f'bible_chapter_{version_id}_{book_id}_{chapter_number}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        chapters = self.get_chapters(book_id, version_id)
        chapter_id = None
        for chapter in chapters:
            if chapter.get('number') == str(chapter_number):
                chapter_id = chapter.get('id')
                break
        
        if not chapter_id:
            logger.warning(f"Chapter not found: {book_id} {chapter_number}")
            return None
        
        params = {
            'content-type': 'html',
            'include-notes': 'true' if include_notes else 'false',
            'include-titles': 'true',
            'include-chapter-numbers': 'false',
            'include-verse-numbers': 'true',
            'include-verse-spans': 'true'
        }
        
        data = self._make_request(f'bibles/{version_id}/chapters/{chapter_id}', params=params)
        if data and 'data' in data:
            chapter_data = data['data']
            if 'content' in chapter_data:
                chapter_data['content'] = sanitize_html(chapter_data['content'])
            cache.set(cache_key, chapter_data, 3600)
            return chapter_data
        return None
    
    def get_verse(self, book_id, chapter_number, verse_number, version_id=None):
        version_id = version_id or self.default_version
        cache_key = f'bible_verse_{version_id}_{book_id}_{chapter_number}_{verse_number}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        verse_id = f"{book_id}.{chapter_number}.{verse_number}"

        params = {
            'content-type': 'html',
            'include-verse-numbers': 'true'
        }

        data = self._make_request(f'bibles/{version_id}/verses/{verse_id}', params=params)
        if data and 'data' in data:
            verse_data = data['data']
            cache.set(cache_key, verse_data, 3600)
            return verse_data
        return None

    def get_chapter_verse_count(self, book_id, chapter_number, version_id=None):
        version_id = version_id or self.default_version
        cache_key = f'bible_verse_count_{version_id}_{book_id}_{chapter_number}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        chapter_data = self.get_chapter(book_id, chapter_number, version_id)
        if not chapter_data:
            return None

        verse_count = chapter_data.get('verseCount')
        if verse_count:
            cache.set(cache_key, verse_count, 86400)
            return verse_count

        content = chapter_data.get('content', '')
        if content:
            import re
            numbers = re.findall(r'data-verse-number="(\d+)"', content)
            if numbers:
                verse_count = max(int(n) for n in numbers)
                cache.set(cache_key, verse_count, 86400)
                return verse_count

        return None
    
    def get_verses(self, book_id, chapter_number, verse_start, verse_end=None, version_id=None):
        version_id = version_id or self.default_version
        
        if verse_end and verse_end != verse_start:
            verse_id = f"{book_id}.{chapter_number}.{verse_start}-{book_id}.{chapter_number}.{verse_end}"
            cache_key = f'bible_verses_{version_id}_{book_id}_{chapter_number}_{verse_start}_{verse_end}'
        else:
            verse_id = f"{book_id}.{chapter_number}.{verse_start}"
            cache_key = f'bible_verse_{version_id}_{book_id}_{chapter_number}_{verse_start}'
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        params = {
            'content-type': 'html',
            'include-verse-numbers': 'true'
        }
        
        data = self._make_request(f'bibles/{version_id}/passages/{verse_id}', params=params)
        if data and 'data' in data:
            passage_data = data['data']
            cache.set(cache_key, passage_data, 3600)
            return passage_data
        return None
    
    def search(self, query, version_id=None, limit=10):
        version_id = version_id or self.default_version
        
        params = {
            'query': query,
            'limit': limit
        }
        
        data = self._make_request(f'bibles/{version_id}/search', params=params)
        if data and 'data' in data:
            return data['data']
        return None
    
    def get_book_id_from_name(self, book_name, version_id=None):
        books = self.get_books(version_id)
        book_name_lower = book_name.lower().strip()
        
        for book in books:
            if book.get('name', '').lower() == book_name_lower:
                return book.get('id')
            if book.get('abbreviation', '').lower() == book_name_lower:
                return book.get('id')
        
        for book in books:
            if book_name_lower in book.get('name', '').lower():
                return book.get('id')
        
        return None
