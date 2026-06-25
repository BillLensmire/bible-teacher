from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reader', '0003_reading_progress_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='readingprogress',
            name='note_source',
            field=models.CharField(blank=True, default='constable', max_length=100),
        ),
    ]
