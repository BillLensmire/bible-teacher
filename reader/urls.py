from django.urls import path
from . import views

app_name = 'reader'

urlpatterns = [
    path('', views.bible_reader, name='bible_reader'),
    path('<str:book>/<int:chapter>/', views.bible_reader, name='bible_reader_chapter'),
    path('sermons/', views.SermonListView.as_view(), name='sermon_list'),
    path('notes/', views.SermonNotesListView.as_view(), name='sermon_notes_list'),
    path('debug-audio/', views.debug_audio, name='debug_audio'),
    path('api/chapter/<str:book>/<int:chapter>/', views.get_chapter_content, name='get_chapter_content'),
    path('api/notes/<str:book>/<int:chapter>/', views.get_chapter_notes, name='get_chapter_notes'),
    path('api/toggle-notes/', views.toggle_note_type, name='toggle_note_type'),
    path('api/progress/save/', views.save_listening_progress, name='save_progress'),
    path('api/progress/<int:sermon_id>/', views.get_listening_progress, name='get_progress'),
]
