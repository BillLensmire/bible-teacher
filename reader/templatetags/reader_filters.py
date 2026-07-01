from django import template

register = template.Library()


@register.filter
def format_duration(duration):
    """Format a timedelta as MM:SS or HH:MM:SS, omitting leading 0 hours."""
    if not duration:
        return ""
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
