from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .models import (
    Pastor, PastorNote, Sermon, SermonPassage, SermonGroup,
    SermonNotePDF, PDFPassage, ListeningProgress, ExternalNote
)
from .services.bible_api import BIBLE_BOOKS

# Override verbose names at runtime to avoid database migrations
Pastor._meta.verbose_name = 'Teacher'
Pastor._meta.verbose_name_plural = 'Teachers'
PastorNote._meta.verbose_name = 'Teacher Note'
PastorNote._meta.verbose_name_plural = 'Teacher Notes'


class SermonPassageForm(forms.ModelForm):
    book = forms.ChoiceField(
        choices=[('', '---------')] + [(b, b) for b in BIBLE_BOOKS],
        required=True
    )
    chapter = forms.IntegerField(
        widget=forms.Select(choices=[('', '---------')]),
        required=True
    )
    verse_start = forms.IntegerField(
        widget=forms.Select(choices=[('', '---------')]),
        required=True
    )
    verse_end = forms.IntegerField(
        widget=forms.Select(choices=[('', '---------')]),
        required=False
    )

    class Meta:
        model = SermonPassage
        fields = ['book', 'chapter', 'verse_start', 'verse_end', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.chapter:
                self.fields['chapter'].widget.choices = [
                    ('', '---------'),
                    (self.instance.chapter, self.instance.chapter)
                ]
            if self.instance.verse_start:
                self.fields['verse_start'].widget.choices = [
                    ('', '---------'),
                    (self.instance.verse_start, self.instance.verse_start)
                ]
            if self.instance.verse_end:
                self.fields['verse_end'].widget.choices = [
                    ('', '---------'),
                    (self.instance.verse_end, self.instance.verse_end)
                ]


class SermonPassageInline(admin.TabularInline):
    model = SermonPassage
    form = SermonPassageForm
    extra = 1
    fields = ['book', 'chapter', 'verse_start', 'verse_end', 'order']

    class Media:
        js = ['admin/js/sermon_passage.js']


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
    inlines = [SermonPassageInline]
    readonly_fields = ['audio_duration']

    def get_inline_instances(self, request, obj=None):
        inline_classes = [SermonPassageInline]
        if settings.ENABLE_BIBLE_STUDY_PAGE:
            inline_classes.append(PastorNoteInline)
        if settings.ENABLE_SERMON_NOTES_PAGE:
            inline_classes.append(SermonPDFInline)
        return [inline_class(self.model, self.admin_site) for inline_class in inline_classes]

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
    actions = ['import_constable_notes_action']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-constable/',
                self.admin_site.admin_view(self.import_constable_view),
                name='reader_externalnote_import_constable',
            ),
        ]
        return custom_urls + urls

    def import_constable_notes_action(self, request, queryset):
        messages.info(request, 'Click the "Import Constable Notes" button at the top to import notes from soniclight.com.')
    import_constable_notes_action.short_description = 'Import Constable Notes'

    def import_constable_view(self, request):
        from .services import ConstableImportService
        service = ConstableImportService()
        results = service.import_all(overwrite=True)
        total_created = sum(r.get('created', 0) for r in results)
        total_updated = sum(r.get('updated', 0) for r in results)
        errors = [r for r in results if 'error' in r]
        messages.success(
            request,
            f'Import complete: {total_created} created, {total_updated} updated, '
            f'{len(errors)} errors.'
        )
        if errors:
            for e in errors:
                messages.error(request, f"{e['book']}: {e['error']}")
        return redirect(reverse('admin:reader_externalnote_changelist'))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


if not settings.ENABLE_BIBLE_STUDY_PAGE:
    admin.site.unregister(ExternalNote)
    admin.site.unregister(PastorNote)

if not settings.ENABLE_SERMON_NOTES_PAGE:
    admin.site.unregister(SermonNotePDF)
    admin.site.unregister(PDFPassage)
