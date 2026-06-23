# Bible API Service

This module provides integration with the API.Bible service for retrieving Bible text.

## BibleAPIService

The main service class for interacting with the API.Bible API.

### Configuration

Set these in `bibleteacher/settings.py`:

```python
BIBLE_API_KEY = 'your-api-key-here'  # Get from https://scripture.api.bible/
DEFAULT_BIBLE_VERSION = 'de4e12af7f28f599-02'  # KJV by default
```

### Usage

```python
from reader.services import BibleAPIService

# Initialize service
bible_service = BibleAPIService()

# Get available Bible versions
versions = bible_service.get_available_versions()

# Get books in a version
books = bible_service.get_books(version_id='de4e12af7f28f599-02')

# Get a chapter
chapter_data = bible_service.get_chapter('JHN', 1, version_id='de4e12af7f28f599-02')

# Get verses
verses = bible_service.get_verses('JHN', 3, 16, 17)

# Search
results = bible_service.search('love', limit=10)
```

### Caching

All API responses are cached in the database to minimize API calls:
- Versions: 24 hours
- Books: 24 hours  
- Chapters: 1 hour
- Verses: 1 hour

### Methods

- `get_available_versions()` - Get list of available English Bible versions
- `get_books(version_id)` - Get list of books in a version
- `get_chapters(book_id, version_id)` - Get list of chapters in a book
- `get_chapter(book_id, chapter_number, version_id)` - Get full chapter content
- `get_verse(book_id, chapter_number, verse_number, version_id)` - Get single verse
- `get_verses(book_id, chapter_number, verse_start, verse_end, version_id)` - Get verse range
- `search(query, version_id, limit)` - Search Bible text
- `get_book_id_from_name(book_name, version_id)` - Convert book name to API book ID
