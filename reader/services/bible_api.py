import requests
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


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
            cache.set(cache_key, versions, 86400)
            return versions
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
            'include-chapter-numbers': 'true',
            'include-verse-numbers': 'true',
            'include-verse-spans': 'true'
        }
        
        data = self._make_request(f'bibles/{version_id}/chapters/{chapter_id}', params=params)
        if data and 'data' in data:
            chapter_data = data['data']
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
