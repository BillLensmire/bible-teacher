from django.contrib import admin
from .models import (
    Pastor, PastorNote, Sermon, SermonPassage, SermonGroup,
    SermonNotePDF, PDFPassage, ListeningProgress, ExternalNote
)


class SermonPassageInline(admin.TabularInline):
    model = SermonPassage
    extra = 1
    fields = ['book', 'chapter', 'verse_start', 'verse_end', 'order']


class PastorNoteInline(admin.TabularInline):
    model = PastorNote
    extra = 0
    fields = ['book', 'chapter', 'verse_start', 'verse_end', 'note_text']


class SermonPDFInline(admin.TabularInline):
    model = SermonNotePDF
    extra = 0
    fields = ['title', 'pdf_file', 'date_created']
    readonly_fields = ['title']


@admin.register(Pastor)
class PastorAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'sermon_count', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def sermon_count(self, obj):
        return obj.sermons.count()
    sermon_count.short_description = 'Sermons'


@admin.register(Sermon)
class SermonAdmin(admin.ModelAdmin):
    list_display = ['title', 'pastor', 'date_preached', 'audio_duration', 'created_at']
    list_filter = ['pastor', 'date_preached', 'groups']
    search_fields = ['title', 'description', 'pastor__name']
    filter_horizontal = ['groups']
    date_hierarchy = 'date_preached'
    inlines = [SermonPassageInline, PastorNoteInline, SermonPDFInline]
    readonly_fields = ['audio_duration']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'pastor', 'date_preached', 'description')
        }),
        ('Audio', {
            'fields': ('audio_file', 'audio_duration'),
            'description': 'Audio duration is automatically extracted when the file is uploaded.'
        }),
        ('Categorization', {
            'fields': ('groups',)
        }),
    )


@admin.register(SermonPassage)
class SermonPassageAdmin(admin.ModelAdmin):
    list_display = ['sermon', 'book', 'chapter', 'verse_start', 'verse_end', 'order']
    list_filter = ['book']
    search_fields = ['sermon__title', 'book']


@admin.register(SermonGroup)
class SermonGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'group_type', 'sermon_count', 'created_at']
    list_filter = ['group_type']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def sermon_count(self, obj):
        return obj.sermons.count()
    sermon_count.short_description = 'Sermons'


class PDFPassageInline(admin.TabularInline):
    model = PDFPassage
    extra = 1
    fields = ['book', 'chapter', 'verse_start', 'verse_end', 'order']


@admin.register(SermonNotePDF)
class SermonNotePDFAdmin(admin.ModelAdmin):
    list_display = ['title', 'pastor', 'sermon', 'date_created', 'created_at']
    list_filter = ['pastor', 'date_created', 'groups']
    search_fields = ['title', 'description', 'pastor__name']
    filter_horizontal = ['groups']
    date_hierarchy = 'date_created'
    inlines = [PDFPassageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'pastor', 'date_created', 'description')
        }),
        ('PDF File', {
            'fields': ('pdf_file',)
        }),
        ('Link to Sermon', {
            'fields': ('sermon',),
            'description': 'Optional: Link this PDF to a specific sermon'
        }),
        ('Categorization', {
            'fields': ('groups',)
        }),
    )


@admin.register(PDFPassage)
class PDFPassageAdmin(admin.ModelAdmin):
    list_display = ['pdf', 'book', 'chapter', 'verse_start', 'verse_end', 'order']
    list_filter = ['book']
    search_fields = ['pdf__title', 'book']


@admin.register(PastorNote)
class PastorNoteAdmin(admin.ModelAdmin):
    list_display = ['sermon', 'book', 'chapter', 'verse_start', 'verse_end', 'created_at']
    list_filter = ['book', 'sermon__pastor']
    search_fields = ['note_text', 'sermon__title']


@admin.register(ListeningProgress)
class ListeningProgressAdmin(admin.ModelAdmin):
    list_display = ['sermon', 'browser_fingerprint', 'current_position', 'last_updated']
    list_filter = ['sermon']
    search_fields = ['browser_fingerprint', 'sermon__title']
    readonly_fields = ['last_updated']


@admin.register(ExternalNote)
class ExternalNoteAdmin(admin.ModelAdmin):
    list_display = ['source', 'book', 'chapter', 'verse_start', 'verse_end', 'fetched_at']
    list_filter = ['source', 'book']
    search_fields = ['book', 'note_text']
    readonly_fields = ['fetched_at']
