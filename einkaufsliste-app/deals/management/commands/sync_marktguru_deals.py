from django.core.management.base import BaseCommand

from deals.models import DealSource, Store, Deal
from deals.providers.marktguru import MarktguruProvider
from deals.services import SYNONYMS
from ingredients.models import Ingredient


COMMON_PRODUCTS = [
    "nudeln", "pasta", "spaghetti", "penne", "reis", "kartoffeln",
    "tomaten", "gurke", "paprika", "salat", "zwiebeln", "knoblauch",
    "karotten", "möhren", "brokkoli", "zucchini", "champignons",
    "äpfel", "bananen", "beeren", "erdbeeren", "trauben",
    "milch", "joghurt", "quark", "käse", "mozzarella", "feta",
    "butter", "sahne", "frischkäse",
    "eier", "hackfleisch", "hähnchen", "pute", "rind", "schwein",
    "lachs", "thunfisch",
    "brot", "toast", "brötchen", "wraps",
    "haferflocken", "müsli", "cornflakes",
    "öl", "olivenöl", "essig", "ketchup", "mayonnaise", "senf",
    "mehl", "zucker", "salz", "pfeffer",
    "schokolade", "chips", "kekse",
    "wasser", "cola", "saft", "kaffee", "tee",
]


def build_search_terms():
    terms = set()

    for name in Ingredient.objects.values_list("name", flat=True):
        if name:
            terms.add(name.lower().strip())

    for key, values in SYNONYMS.items():
        terms.add(key.lower().strip())
        for value in values:
            terms.add(value.lower().strip())

    for product in COMMON_PRODUCTS:
        terms.add(product.lower().strip())

    return sorted(term for term in terms if len(term) >= 3)


class Command(BaseCommand):
    help = "Importiert aktuelle Angebote von Marktguru."

    def add_arguments(self, parser):
        parser.add_argument("--query", nargs="*", default=None)
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--keep-old", action="store_true")
        parser.add_argument("--show-terms", action="store_true")

    def handle(self, *args, **options):
        provider = MarktguruProvider()

        source, _ = DealSource.objects.get_or_create(
            name=provider.source_name,
            defaults={"base_url": "https://www.marktguru.de"},
        )

        search_terms = options["query"] or build_search_terms()

        if options["show_terms"]:
            self.stdout.write(", ".join(search_terms))
            self.stdout.write(f"{len(search_terms)} Suchbegriffe")
            return

        if not options["keep_old"]:
            deleted_count, _ = Deal.objects.filter(source=source).delete()
            self.stdout.write(f"{deleted_count} alte Marktguru-Angebote gelöscht.")

        imported_deals = provider.fetch_deals(
            search_terms=search_terms,
            limit=options["limit"],
        )

        saved_count = 0

        for imported in imported_deals:
            store, _ = Store.objects.get_or_create(
                name=imported.store_name,
                defaults={
                    "location": "",
                    "postal_code": provider.zip_code,
                },
            )

            Deal.objects.update_or_create(
                source=source,
                external_id=imported.external_id,
                defaults={
                    "store": store,
                    "title": imported.title,
                    "description": imported.description,
                    "original_price": imported.original_price,
                    "deal_price": imported.deal_price,
                    "discount_text": imported.discount_text,
                    "product_url": imported.product_url,
                    "image_url": imported.image_url,
                    "valid_from": imported.valid_from,
                    "valid_until": imported.valid_until,
                },
            )

            saved_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{saved_count} Marktguru-Angebote importiert mit {len(search_terms)} Suchbegriffen."
            )
        )