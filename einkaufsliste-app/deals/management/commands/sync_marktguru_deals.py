from django.core.management.base import BaseCommand

from deals.sync import build_search_terms, sync_marktguru, SyncAlreadyRunning


class Command(BaseCommand):
    help = "Importiert aktuelle Angebote von Marktguru."

    def add_arguments(self, parser):
        parser.add_argument("--query", nargs="*", default=None)
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--keep-old", action="store_true")
        parser.add_argument("--show-terms", action="store_true")

    def handle(self, *args, **options):
        search_terms = options["query"] or build_search_terms()

        if options["show_terms"]:
            self.stdout.write(", ".join(search_terms))
            self.stdout.write(f"{len(search_terms)} Suchbegriffe")
            return

        try:
            saved_count = sync_marktguru(
                limit=options["limit"],
                search_terms=search_terms,
                keep_old=options["keep_old"],
            )
        except SyncAlreadyRunning as error:
            self.stdout.write(self.style.WARNING(str(error)))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"{saved_count} Marktguru-Angebote importiert mit {len(search_terms)} Suchbegriffen."
            )
        )
