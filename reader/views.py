from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.decorators import method_decorator
from django.conf import settings
from .models import (
    Sermon, SermonNotePDF, PastorNote, ExternalNote,
    Pastor, SermonGroup, ListeningProgress, ReadingProgress
)
import json
from .services import BibleAPIService
from .services.bible_api import sanitize_html
import logging
import re

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def debug_audio(request):
    """Debug page for audio progress tracking"""
    if not settings.DEBUG:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, 'reader/debug_audio.html')


def bible_reader(request, book=None, chapter=None):
    """Main Bible study page with two-pane layout"""
    if not settings.ENABLE_BIBLE_STUDY_PAGE:
        raise Http404("Bible Study page is not enabled.")
    if not book and not chapter:
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if re.search(r'android|webos|iphone|ipad|ipod|blackberry|windows phone|opera mini|mobile', user_agent):
            referer = request.META.get('HTTP_REFERER', '')
            if not referer or request.get_host() not in referer:
                return redirect('reader:sermon_list')
    version_id = request.GET.get('version') or request.session.get('bible_version')
    if version_id:
        request.session['bible_version'] = version_id

    try:
        bible_service = BibleAPIService()
        books = bible_service.get_books(version_id)
        versions = bible_service.get_available_versions()
    except Exception as e:
        logger.error(f"Failed to load Bible data: {e}")
        books = []
        versions = []
    
    chapter_content = None
    if book and chapter:
        try:
            bible_service = BibleAPIService()
            book_id = bible_service.get_book_id_from_name(book, version_id)
            if book_id:
                chapter_content = bible_service.get_chapter(book_id, int(chapter), version_id)
        except Exception as e:
            logger.error(f"Failed to load chapter: {e}")
    
    note_source = request.session.get('note_source', 'constable')
    pastors = Pastor.objects.all().order_by('name')

    context = {
        'note_source': note_source,
        'pastors': pastors,
        'books': books,
        'versions': versions,
        'current_version': version_id,
        'current_book': book,
        'current_chapter': chapter,
        'chapter_content': chapter_content
    }
    return render(request, 'reader/bible_reader.html', context)


def get_chapter_content(request, book, chapter):
    """API endpoint to get Bible chapter content"""
    version_id = request.GET.get('version') or request.session.get('bible_version')
    if version_id:
        request.session['bible_version'] = version_id
    
    try:
        bible_service = BibleAPIService()
        book_id = bible_service.get_book_id_from_name(book, version_id)
        
        if not book_id:
            return JsonResponse({'error': 'Book not found'}, status=404)
        
        chapter_data = bible_service.get_chapter(book_id, int(chapter), version_id)
        
        if not chapter_data:
            return JsonResponse({'error': 'Chapter not found'}, status=404)
        
        return JsonResponse({
            'content': chapter_data.get('content', ''),
            'reference': chapter_data.get('reference', ''),
            'book': book,
            'chapter': chapter
        })
    except Exception as e:
        logger.error(f"Error fetching chapter content: {e}")
        return JsonResponse({'error': 'An error occurred while fetching chapter content'}, status=500)


def get_chapter_nav(request, book, chapter):
    """API endpoint to get next/prev chapter for continuous scrolling"""
    version_id = request.GET.get('version') or request.session.get('bible_version')
    if version_id:
        request.session['bible_version'] = version_id

    try:
        bible_service = BibleAPIService()
        books = bible_service.get_books(version_id)

        current_idx = None
        for i, b in enumerate(books):
            if b.get('name', '').lower() == book.lower():
                current_idx = i
                break

        if current_idx is None:
            return JsonResponse({'error': 'Book not found'}, status=404)

        current_book = books[current_idx]
        chapters = bible_service.get_chapters(current_book['id'], version_id)
        chapter_numbers = sorted([int(c['number']) for c in chapters if c['number'].isdigit()])

        current_chapter = int(chapter)

        next_nav = None
        if current_chapter + 1 in chapter_numbers:
            next_nav = {'book': current_book['name'], 'chapter': current_chapter + 1}
        elif current_idx + 1 < len(books):
            next_book = books[current_idx + 1]
            next_chapters = bible_service.get_chapters(next_book['id'], version_id)
            next_nums = sorted([int(c['number']) for c in next_chapters if c['number'].isdigit()])
            if next_nums:
                next_nav = {'book': next_book['name'], 'chapter': next_nums[0]}

        prev_nav = None
        if current_chapter - 1 in chapter_numbers:
            prev_nav = {'book': current_book['name'], 'chapter': current_chapter - 1}
        elif current_idx - 1 >= 0:
            prev_book = books[current_idx - 1]
            prev_chapters = bible_service.get_chapters(prev_book['id'], version_id)
            prev_nums = sorted([int(c['number']) for c in prev_chapters if c['number'].isdigit()])
            if prev_nums:
                prev_nav = {'book': prev_book['name'], 'chapter': prev_nums[-1]}

        return JsonResponse({'next': next_nav, 'prev': prev_nav})
    except Exception as e:
        logger.error(f"Error fetching chapter nav: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


def get_book_chapters(request, book):
    """API endpoint to get all chapter numbers for a given book"""
    version_id = request.GET.get('version') or request.session.get('bible_version')
    if version_id:
        request.session['bible_version'] = version_id

    try:
        bible_service = BibleAPIService()
        book_id = bible_service.get_book_id_from_name(book, version_id)
        if not book_id:
            return JsonResponse({'error': 'Book not found'}, status=404)
        chapters = bible_service.get_chapters(book_id, version_id)
        chapter_numbers = sorted([int(c['number']) for c in chapters if c['number'].isdigit()])
        return JsonResponse({'chapters': chapter_numbers})
    except Exception as e:
        logger.error(f"Error fetching book chapters: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


def get_chapter_notes(request, book, chapter):
    """API endpoint to get notes for a specific chapter"""
    note_source = request.session.get('note_source', 'constable')

    if note_source == 'constable':
        notes = ExternalNote.objects.filter(
            source='constable',
            book__iexact=book,
            chapter=chapter
        ).order_by('verse_start')
        note_type = 'constable'
    else:
        notes = PastorNote.objects.filter(
            book__iexact=book,
            chapter=chapter
        ).select_related('sermon', 'sermon__pastor').order_by('verse_start')
        note_type = 'pastor'
        if note_source.startswith('pastor:'):
            try:
                pastor_id = int(note_source.split(':')[1])
                notes = notes.filter(sermon__pastor_id=pastor_id)
            except (ValueError, IndexError):
                pass

    for note in notes:
        note.note_text = sanitize_html(note.note_text)

    notes_html = render(request, 'reader/notes_fragment.html', {
        'notes': notes,
        'book': book,
        'chapter': chapter,
        'note_type': note_type
    }).content.decode('utf-8')

    return JsonResponse({'html': notes_html})


@csrf_protect
def set_note_source(request):
    """Set the note source (constable or pastor:<id>) in session"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    note_source = data.get('note_source', 'constable')
    if note_source != 'constable' and not note_source.startswith('pastor:'):
        return JsonResponse({'status': 'error', 'message': 'Invalid note_source'}, status=400)

    request.session['note_source'] = note_source

    fingerprint = data.get('fingerprint')
    if fingerprint and isinstance(fingerprint, str) and len(fingerprint) <= 64:
        ReadingProgress.objects.update_or_create(
            browser_fingerprint=fingerprint,
            defaults={'note_source': note_source}
        )

    return JsonResponse({'status': 'success', 'note_source': note_source})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class SermonListView(ListView):
    """List view for all sermons with filtering"""
    model = Sermon
    template_name = 'reader/sermon_list.html'
    context_object_name = 'sermons'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Sermon.objects.select_related('pastor').prefetch_related(
            'passages', 'groups'
        )
        
        # Filter by pastor
        pastor_id = self.request.GET.get('pastor')
        if pastor_id:
            queryset = queryset.filter(pastor_id=pastor_id)
        
        # Filter by book
        book = self.request.GET.get('book')
        if book:
            queryset = queryset.filter(passages__book=book).distinct()
        
        # Filter by group
        group_id = self.request.GET.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(pastor__name__icontains=search)
            )
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pastors'] = Pastor.objects.all()
        context['groups'] = SermonGroup.objects.all()
        return context


class SermonNotesListView(ListView):
    """List view for sermon note PDFs"""
    model = SermonNotePDF
    template_name = 'reader/sermon_notes_list.html'
    context_object_name = 'pdfs'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not settings.ENABLE_SERMON_NOTES_PAGE:
            raise Http404("Sermon Notes page is not enabled.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = SermonNotePDF.objects.select_related('pastor', 'sermon').prefetch_related(
            'passages', 'groups'
        )
        
        # Filter by pastor
        pastor_id = self.request.GET.get('pastor')
        if pastor_id:
            queryset = queryset.filter(pastor_id=pastor_id)
        
        # Filter by book
        book = self.request.GET.get('book')
        if book:
            queryset = queryset.filter(passages__book=book).distinct()
        
        # Filter by group
        group_id = self.request.GET.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
        
        # Filter by attached/standalone
        attached = self.request.GET.get('attached')
        if attached == 'yes':
            queryset = queryset.filter(sermon__isnull=False)
        elif attached == 'no':
            queryset = queryset.filter(sermon__isnull=True)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(pastor__name__icontains=search)
            )
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pastors'] = Pastor.objects.all()
        context['groups'] = SermonGroup.objects.all()
        return context


@csrf_protect
def save_listening_progress(request):
    """API endpoint to save sermon listening progress"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    fingerprint = data.get('fingerprint')
    sermon_id = data.get('sermon_id')
    position = data.get('position')

    if not fingerprint or not isinstance(fingerprint, str) or len(fingerprint) > 64:
        return JsonResponse({'status': 'error', 'message': 'Invalid fingerprint'}, status=400)
    if not sermon_id:
        return JsonResponse({'status': 'error', 'message': 'Invalid sermon_id'}, status=400)
    if position is None or not isinstance(position, (int, float)) or position < 0:
        return JsonResponse({'status': 'error', 'message': 'Invalid position'}, status=400)

    try:
        sermon_id = int(sermon_id)
        position = int(position)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid sermon_id or position'}, status=400)

    try:
        sermon = Sermon.objects.get(id=sermon_id)
    except Sermon.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sermon not found'}, status=404)

    progress, created = ListeningProgress.objects.update_or_create(
        browser_fingerprint=fingerprint,
        sermon=sermon,
        defaults={'current_position': position}
    )
    return JsonResponse({'status': 'success', 'position': position})


def get_listening_progress(request, sermon_id):
    """API endpoint to get sermon listening progress"""
    fingerprint = request.GET.get('fingerprint')

    if not fingerprint or len(fingerprint) > 64:
        return JsonResponse({'status': 'error', 'message': 'Invalid fingerprint'}, status=400)

    try:
        progress = ListeningProgress.objects.get(
            browser_fingerprint=fingerprint,
            sermon_id=sermon_id
        )
        return JsonResponse({
            'status': 'success',
            'position': progress.current_position
        })
    except ListeningProgress.DoesNotExist:
        return JsonResponse({'status': 'success', 'position': 0})
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@csrf_protect
def save_reading_progress(request):
    """API endpoint to save Bible reading position"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    fingerprint = data.get('fingerprint')
    book = data.get('book')
    chapter = data.get('chapter')
    version = data.get('version', '')

    if not fingerprint or not isinstance(fingerprint, str) or len(fingerprint) > 64:
        return JsonResponse({'status': 'error', 'message': 'Invalid fingerprint'}, status=400)
    if not book or not isinstance(book, str):
        return JsonResponse({'status': 'error', 'message': 'Invalid book'}, status=400)
    if chapter is None or not isinstance(chapter, int) or chapter < 1:
        return JsonResponse({'status': 'error', 'message': 'Invalid chapter'}, status=400)
    if not isinstance(version, str) or len(version) > 100:
        return JsonResponse({'status': 'error', 'message': 'Invalid version'}, status=400)

    print(f"Saving reading progress: {fingerprint} {book} {chapter} {version}")
    
    ReadingProgress.objects.update_or_create(
        browser_fingerprint=fingerprint,
        defaults={'book': book, 'chapter': chapter, 'version': version}
    )
    return JsonResponse({'status': 'success', 'book': book, 'chapter': chapter})


def get_reading_progress(request):
    """API endpoint to get Bible reading position"""
    fingerprint = request.GET.get('fingerprint')

    if not fingerprint or len(fingerprint) > 64:
        return JsonResponse({'status': 'error', 'message': 'Invalid fingerprint'}, status=400)

    try:
        progress = ReadingProgress.objects.get(browser_fingerprint=fingerprint)
        request.session['note_source'] = progress.note_source
        return JsonResponse({
            'status': 'success',
            'book': progress.book,
            'chapter': progress.chapter,
            'version': progress.version,
            'note_source': progress.note_source
        })
    except ReadingProgress.DoesNotExist:
        return JsonResponse({'status': 'success', 'book': None, 'chapter': None, 'version': None, 'note_source': None})
