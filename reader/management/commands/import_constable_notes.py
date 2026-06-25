from django.core.management.base import BaseCommand
from reader.services import ConstableImportService
from reader.services.constable_import import BOOK_SLUGS


class Command(BaseCommand):
    help = 'Import Dr. Constable\'s expository notes from soniclight.com'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book',
            type=str,
            help='Import a single book by name (e.g., "Genesis", "John")',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing notes instead of skipping them',
        )
        parser.add_argument(
            '--list-books',
            action='store_true',
            help='List all available book names and exit',
        )

    def handle(self, *args, **options):
        if options['list_books']:
            self.stdout.write('Available books:')
            for name in BOOK_SLUGS:
                self.stdout.write(f'  {name}')
            return

        service = ConstableImportService()
        overwrite = options['overwrite']

        if options['book']:
            book_name = options['book'].strip()
            if book_name not in BOOK_SLUGS:
                self.stderr.write(
                    self.style.ERROR(f'Unknown book: "{book_name}"')
                )
                self.stderr.write('Use --list-books to see available options.')
                return
            results = service.import_all(
                overwrite=overwrite,
                book_names=[book_name],
            )
        else:
            self.stdout.write('Importing all 66 books from soniclight.com...')
            results = service.import_all(overwrite=overwrite)

        total_created = 0
        total_updated = 0
        total_errors = 0

        for r in results:
            if 'error' in r:
                total_errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"  {r['book']}: FAILED - {r['error']}"
                    )
                )
            else:
                total_created += r['created']
                total_updated += r['updated']
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {r['book']}: {r['created']} created, "
                        f"{r['updated']} updated "
                        f"({r['parsed']} parsed)"
                    )
                )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done: {total_created} created, {total_updated} updated, '
                f'{total_errors} errors'
            )
        )
