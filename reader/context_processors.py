from django.conf import settings


def feature_flags(request):
    """Expose feature flag settings to all templates."""
    return {
        'ENABLE_BIBLE_STUDY_PAGE': getattr(settings, 'ENABLE_BIBLE_STUDY_PAGE', False),
        'ENABLE_SERMON_NOTES_PAGE': getattr(settings, 'ENABLE_SERMON_NOTES_PAGE', False),
    }
