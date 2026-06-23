## Bible Teacher Website

A comprehensive Bible study platform with sermon audio management, pastor notes, and Dr. Constable's notes integration.

## Features

### ✅ Implemented

#### Database Models

*   **Pastor Management**: Multiple pastors/teachers with sermon tracking
*   **Sermon Audio**: Upload and manage sermon audio files with metadata
*   **Multiple Passage References**: Each sermon can reference multiple Bible passages
*   **Sermon Grouping**: Organize sermons by series, theme, topic, book, etc.
*   **PDF Sermon Notes**: Upload and manage sermon notes PDFs
*   **Listening Progress**: Track playback position without user accounts (browser fingerprinting)
*   **External Notes**: Cache for Dr. Constable's notes

#### User Interface

*   **Bible Reader**: Two-pane layout with automatic chapter synchronization
    *   Real Bible text from API.Bible service
    *   Dynamic book and chapter navigation
    *   Multiple Bible version support
    *   Left pane: Bible text with scroll detection
    *   Right pane: Notes that auto-update when scrolling to new chapter
    *   Toggle between pastor notes and Constable notes
    *   Smooth fade transitions
    *   Direct chapter URLs for sharing
*   **Sermon Library**: Browse and filter sermons
    *   Filter by pastor, book, group
    *   Search functionality
    *   Enhanced audio player with:
        *   Automatic progress tracking (saves every 5 seconds)
        *   Resume from last position
        *   Playback speed control (0.5x - 2x)
        *   Time display (current / total)
    *   Display sermon passages and groups
*   **Notes Library**: Browse sermon note PDFs
    *   Filter by pastor, group, attached/standalone
    *   View and download PDFs
    *   Link to associated sermons

#### Bible API Integration

*   **API.Bible Service**: Full integration with scripture.api.bible
    *   Multiple Bible versions (KJV, NIV, ESV, etc.)
    *   Database caching (1-24 hour TTL)
    *   Book, chapter, and verse retrieval
    *   Search functionality
    *   Flexible book name matching

#### Audio Features

*   **Browser Fingerprinting**: Unique device identification
    *   Canvas and WebGL fingerprinting
    *   Font detection
    *   Hardware and screen metrics
    *   SHA-256 hashing for privacy
*   **Progress Tracking**: Resume sermons where you left off
    *   Works across sessions
    *   No user account required
    *   Automatic save every 5 seconds
    *   Visual resume notification

#### Admin Interface

*   Comprehensive Django admin for all models
*   Inline editing for passages and notes
*   Custom list displays with counts
*   Filtering and search
*   File upload validation
*   **Audio duration auto-extraction** using mutagen
    *   Automatic when uploading sermon audio
    *   Supports MP3, WAV, OGG, M4A

### 🚧 To Be Implemented

*   Verse-note linking and highlighting
*   Word document import for pastor notes
*   Dr. Constable's notes import from soniclight.com
*   Rich text editor for notes
*   Comprehensive test suite
*   Keyboard shortcuts for audio player

## Installation

### Prerequisites

*   Python 3.10+
*   PostgreSQL 12+
*   Virtual environment (venv)

### Setup

**Clone the repository** (if applicable)

**Activate virtual environment**

**Install dependencies**

**Create PostgreSQL database**

**Run migrations**

**Create superuser**

**Run development server**

**Access the application**

*   Main site: http://localhost:8000/
*   Admin: http://localhost:8000/admin/
*   Sermons: http://localhost:8000/sermons/
*   Notes: http://localhost:8000/notes/

## Project Structure

```plaintext
bible-teacher/
├── bibleteacher/          # Django project
│   ├── settings.py        # PostgreSQL, media files configured
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py
├── reader/                # Main app
│   ├── models.py          # All 9 database models
│   ├── views.py           # Class-based views and API endpoints
│   ├── urls.py            # App URL patterns
│   ├── admin.py           # Comprehensive admin interface
│   ├── templates/reader/
│   │   ├── base.html
│   │   ├── bible_reader.html      # Two-pane Bible study page
│   │   ├── sermon_list.html       # Sermon audio library
│   │   ├── sermon_notes_list.html # PDF notes library
│   │   └── notes_fragment.html    # AJAX notes template
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── services/          # To be implemented
│   └── tests/             # To be implemented
├── media/
│   ├── sermons/           # Audio files
│   └── sermon_notes/      # PDF files
├── requirements.txt
└── manage.py
```

## Database Models

### 1\. Pastor

*   Manages multiple teachers/pastors
*   Auto-generated slugs for URLs
*   Tracks sermon count

### 2\. Sermon

*   Title, date, description
*   Links to Pastor (ForeignKey)
*   Audio file with duration
*   Many-to-many with SermonGroup

### 3\. SermonPassage

*   Multiple Bible passages per sermon
*   Book, chapter, verse range support
*   Ordered display

### 4\. SermonGroup

*   Organize by series, theme, topic, book, author
*   Many-to-many with Sermons and PDFs

### 5\. SermonNotePDF

*   PDF sermon notes
*   Can be attached to sermon or standalone
*   Links to Pastor
*   Many-to-many with SermonGroup

### 6\. PDFPassage

*   Multiple Bible passages per PDF
*   Same structure as SermonPassage

### 7\. PastorNote

*   Individual note entries
*   Links to Sermon
*   Verse range support

### 8\. ListeningProgress

*   Browser fingerprint + sermon
*   Current position in seconds
*   Auto-updated timestamp

### 9\. ExternalNote

*   Cache for Constable notes
*   Source, book, chapter, verse
*   Fetched timestamp

## Key Features

### Chapter Scroll Synchronization

The Bible reader automatically updates notes when you scroll to a new chapter:

1.  **Intersection Observer API** detects when a chapter becomes 50%+ visible
2.  **AJAX request** loads notes for that chapter
3.  **Smooth fade transition** updates the notes pane
4.  **Caching** prevents redundant API calls
5.  **Toggle** between pastor notes and Constable notes

### Multiple Passage References

Sermons and PDFs can reference multiple Bible passages:

*   **Single verse**: Genesis 1:1
*   **Verse range**: Genesis 1:1-5
*   **Multiple passages**: Genesis 1:1-5, John 3:16, Romans 8:28-30
*   **Ordered display**: Passages shown in specified order

### Flexible Filtering

Both sermon and PDF libraries support:

*   Filter by pastor
*   Filter by book (any passage matches)
*   Filter by group (series, theme, topic)
*   Search by title, description, pastor name
*   Filter PDFs by attached/standalone

## API Endpoints

*   `GET /api/notes/<book>/<chapter>/` - Get notes for a chapter
*   `POST /api/toggle-notes/` - Toggle between pastor/Constable notes
*   `POST /api/progress/save/` - Save listening progress
*   `GET /api/progress/<sermon_id>/` - Get listening progress

## Admin Features

### Pastor Admin

*   CRUD operations
*   Display sermon count
*   Prepopulated slug

### Sermon Admin

*   Audio file upload with validation
*   Inline passage editing
*   Inline note editing
*   Inline PDF display
*   Group assignment (multi-select)
*   Filtering by pastor, date, groups

### SermonNotePDF Admin

*   PDF file upload with validation
*   Inline passage editing
*   Optional sermon linking
*   Group assignment
*   Filtering by pastor, date, groups

### SermonGroup Admin

*   CRUD operations
*   Display sermon count
*   Filter by group type

## Technologies

*   **Backend**: Django 6.0.6
*   **Database**: PostgreSQL
*   **Frontend**: TailwindCSS (CDN), Vanilla JavaScript
*   **File Storage**: Local filesystem
*   **Testing**: pytest-django, coverage, factory-boy

## Development

### Running Tests

```plaintext
python manage.py test
```

### Code Coverage

```plaintext
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Creating Sample Data

Use Django admin to create:

1.  Pastors
2.  Sermon groups
3.  Sermons with passages
4.  Pastor notes
5.  PDF notes with passages

## Next Steps

See `IMPLEMENTATION_STATUS.md` for detailed progress and next steps.

Priority items:

1.  Bible API integration (API.Bible)
2.  Audio duration auto-extraction
3.  Browser fingerprinting implementation
4.  Word document import
5.  Constable notes import
6.  Comprehensive testing

## License

All rights reserved.

## Support

For issues or questions, please contact the development team.  
 

```plaintext
python manage.py runserver
```

```plaintext
python manage.py createsuperuser
```

```plaintext
python manage.py migrate
```

```plaintext
sudo -u postgres psql
CREATE DATABASE bibleteacher;
\q
```

```plaintext
pip install -r requirements.txt
```

```plaintext
source venv/bin/activate
```

```plaintext
cd /home/bill/devai/bible-teacher
```