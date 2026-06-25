from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from mutagen import File as MutagenFile
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Pastor(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PastorNote(models.Model):
    book = models.CharField(max_length=100)
    chapter = models.IntegerField()
    verse_start = models.IntegerField()
    verse_end = models.IntegerField(null=True, blank=True)
    note_text = models.TextField()
    sermon = models.ForeignKey('Sermon', on_delete=models.CASCADE, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['book', 'chapter', 'verse_start']
        indexes = [
            models.Index(fields=['book', 'chapter', 'verse_start']),
        ]

    def __str__(self):
        verse_ref = f"{self.book} {self.chapter}:{self.verse_start}"
        if self.verse_end:
            verse_ref += f"-{self.verse_end}"
        return verse_ref


class Sermon(models.Model):
    title = models.CharField(max_length=300)
    date_preached = models.DateField()
    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='sermons')
    audio_file = models.FileField(
        upload_to='sermons/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])]
    )
    audio_duration = models.DurationField(null=True, blank=True)
    description = models.TextField(blank=True)
    groups = models.ManyToManyField('SermonGroup', related_name='sermons', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_preached']

    def __str__(self):
        return f"{self.title} - {self.pastor.name}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if self.audio_file and not self.audio_duration:
            try:
                audio = MutagenFile(self.audio_file.path)
                if audio and hasattr(audio.info, 'length'):
                    duration_seconds = int(audio.info.length)
                    self.audio_duration = timedelta(seconds=duration_seconds)
                    logger.info(f"Extracted audio duration: {self.audio_duration} for {self.title}")
                    super().save(update_fields=['audio_duration'])
            except Exception as e:
                logger.warning(f"Could not extract audio duration for {self.title}: {e}")


class SermonPassage(models.Model):
    sermon = models.ForeignKey(Sermon, on_delete=models.CASCADE, related_name='passages')
    book = models.CharField(max_length=100)
    chapter = models.IntegerField()
    verse_start = models.IntegerField()
    verse_end = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'book', 'chapter', 'verse_start']
        indexes = [
            models.Index(fields=['sermon', 'order']),
            models.Index(fields=['book', 'chapter']),
        ]

    def __str__(self):
        verse_ref = f"{self.book} {self.chapter}:{self.verse_start}"
        if self.verse_end:
            verse_ref += f"-{self.verse_end}"
        return verse_ref


class SermonGroup(models.Model):
    GROUP_TYPES = [
        ('series', 'Series'),
        ('theme', 'Theme'),
        ('topic', 'Topic'),
        ('book', 'Book'),
        ('author', 'Author'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES, default='other')
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SermonNotePDF(models.Model):
    title = models.CharField(max_length=300)
    pdf_file = models.FileField(
        upload_to='sermon_notes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    pastor = models.ForeignKey(Pastor, on_delete=models.CASCADE, related_name='pdfs')
    sermon = models.ForeignKey(Sermon, on_delete=models.SET_NULL, null=True, blank=True, related_name='pdfs')
    date_created = models.DateField()
    description = models.TextField(blank=True)
    groups = models.ManyToManyField(SermonGroup, related_name='pdfs', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name = 'Sermon Note PDF'
        verbose_name_plural = 'Sermon Note PDFs'

    def __str__(self):
        return self.title


class PDFPassage(models.Model):
    pdf = models.ForeignKey(SermonNotePDF, on_delete=models.CASCADE, related_name='passages')
    book = models.CharField(max_length=100)
    chapter = models.IntegerField()
    verse_start = models.IntegerField()
    verse_end = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'book', 'chapter', 'verse_start']
        indexes = [
            models.Index(fields=['pdf', 'order']),
            models.Index(fields=['book', 'chapter']),
        ]

    def __str__(self):
        verse_ref = f"{self.book} {self.chapter}:{self.verse_start}"
        if self.verse_end:
            verse_ref += f"-{self.verse_end}"
        return verse_ref


class ListeningProgress(models.Model):
    browser_fingerprint = models.CharField(max_length=64, db_index=True)
    sermon = models.ForeignKey(Sermon, on_delete=models.CASCADE, related_name='progress_records')
    current_position = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['browser_fingerprint', 'sermon']
        indexes = [
            models.Index(fields=['browser_fingerprint', 'sermon']),
        ]
        verbose_name_plural = 'Listening Progress'

    def __str__(self):
        return f"{self.sermon.title} - {self.current_position}s"


class ReadingProgress(models.Model):
    browser_fingerprint = models.CharField(max_length=64, db_index=True)
    book = models.CharField(max_length=100)
    chapter = models.IntegerField(default=1)
    version = models.CharField(max_length=100, blank=True, default='')
    note_source = models.CharField(max_length=100, blank=True, default='constable')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Reading Progress'

    def __str__(self):
        return f"{self.book} {self.chapter} - {self.browser_fingerprint[:16]}"


class ExternalNote(models.Model):
    source = models.CharField(max_length=100, default='constable')
    book = models.CharField(max_length=100)
    chapter = models.IntegerField()
    verse_start = models.IntegerField()
    verse_end = models.IntegerField(null=True, blank=True)
    note_text = models.TextField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['book', 'chapter', 'verse_start']
        indexes = [
            models.Index(fields=['source', 'book', 'chapter', 'verse_start']),
        ]

    def __str__(self):
        verse_ref = f"{self.book} {self.chapter}:{self.verse_start}"
        if self.verse_end:
            verse_ref += f"-{self.verse_end}"
        return f"{self.source}: {verse_ref}"
