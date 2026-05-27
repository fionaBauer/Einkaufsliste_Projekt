from django.core.management.base import BaseCommand

from deals.models import DealSource, Store, Deal
from deals.providers.open_prices import OpenPricesProvider


class Command(BaseCommand):
    help = "Importiert echte Preis-/Angebotsdaten aus externen Quellen."

    def handle(self, *args, **options):
        provider = OpenPricesProvider()

        source, _ = DealSource.objects.get_or_create(
            name=provider.source_name,
            defaults={"base_url": provider.base_url},
        )

        imported_deals = provider.fetch_deals()

        saved_count = 0

        for imported in imported_deals:
            store, _ = Store.objects.get_or_create(
                name=imported.store_name,
                defaults={
                    "location": "",
                    "postal_code": "",
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
            self.style.SUCCESS(f"{saved_count} echte Preis-/Deal-Daten importiert.")
        )