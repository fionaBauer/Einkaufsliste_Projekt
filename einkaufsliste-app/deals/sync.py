from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from deals.models import DealSource, Store, Deal
from deals.providers.marktguru import MarktguruProvider
from deals.services import SYNONYMS
from ingredients.models import Ingredient

# Falls ein Prozess waehrend eines Syncs abstuerzt/neu startet, bliebe is_syncing sonst
# fuer immer haengen. Nach dieser Zeit gilt ein Lock als verwaist und darf neu geclaimt werden.
STALE_SYNC_LOCK_AFTER = timedelta(minutes=15)


def claim_sync(source_name, base_url=""):
    """
    Atomarer "Claim" per einzelnem DB-UPDATE (kein Python-Lock, da das nur innerhalb
    eines einzelnen Prozesses gilt - bei mehreren Gunicorn-Workern braeuchte man sonst
    pro Worker ein eigenes Lock, das sich gegenseitig nicht sieht).
    Gibt die DealSource zurueck, wenn der Claim erfolgreich war, sonst None.
    """
    source, _ = DealSource.objects.get_or_create(
        name=source_name, defaults={"base_url": base_url},
    )

    stale_cutoff = timezone.now() - STALE_SYNC_LOCK_AFTER
    claimed = DealSource.objects.filter(pk=source.pk).filter(
        Q(is_syncing=False) | Q(sync_started_at__lt=stale_cutoff)
    ).update(is_syncing=True, sync_started_at=timezone.now())

    return source if claimed else None


def release_sync(source, error=None):
    if error is None:
        DealSource.objects.filter(pk=source.pk).update(
            is_syncing=False, last_synced_at=timezone.now(), last_sync_error="",
        )
    else:
        DealSource.objects.filter(pk=source.pk).update(
            is_syncing=False, last_sync_error=str(error)[:2000],
        )


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

    for ingredient in Ingredient.objects.values_list("name", flat=True):
        if ingredient:
            terms.add(ingredient.lower().strip())

    for key, values in SYNONYMS.items():
        terms.add(key.lower().strip())

        for value in values:
            terms.add(value.lower().strip())

    for product in COMMON_PRODUCTS:
        terms.add(product.lower().strip())

    return sorted(term for term in terms if len(term) >= 3)


class SyncAlreadyRunning(Exception):
    pass


def sync_marktguru(zip_code=None, limit=50, search_terms=None, keep_old=False):
    """
    Selbststaendig: claimt/released das is_syncing-Lock selbst, damit das egal von wo
    aus sicher aufgerufen werden kann (Web-View, Management-Command, Cron, ...) - zwei
    gleichzeitige Aufrufe koennen sich nicht mehr in die Quere kommen.

    search_terms: optional eigene Suchbegriffe statt der automatisch generierten
    (z.B. fuer manuelle Command-Line-Aufrufe mit --query).
    keep_old: bestehende Deals NICHT loeschen, nur neue/aktualisierte reinmergen.
    """
    provider = MarktguruProvider(zip_code=zip_code)

    source = claim_sync(provider.source_name, "https://www.marktguru.de")
    if source is None:
        raise SyncAlreadyRunning(
            f"Ein Sync von '{provider.source_name}' laeuft bereits."
        )

    try:
        # Erst abrufen, dann loeschen+neu anlegen: schlaegt fetch_deals fehl
        # (Netzwerk/API-Fehler), bleiben die bisherigen Deals erhalten statt dass
        # der Nutzer mit leeren Haenden dasteht.
        imported_deals = provider.fetch_deals(
            search_terms=search_terms if search_terms is not None else build_search_terms(),
            limit=limit,
        )

        if not keep_old:
            Deal.objects.filter(source=source).delete()

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

        release_sync(source)
        return saved_count
    except Exception as error:
        release_sync(source, error=error)
        raise