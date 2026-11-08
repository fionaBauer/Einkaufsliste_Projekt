from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from deals.models import DealSource, Store, Deal
from deals.providers.marktguru import MarktguruProvider
from deals.services import SYNONYMS, search_name
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


def used_ingredient_names(household=None):
    """Zutaten, die tatsächlich genutzt werden (Einkaufsliste, Rezepte, Inventar).

    Früher wurde nach JEDER Zutat gesucht – mit dem Lebensmittel-Wörterbuch wären das
    ~300 Anfragen. Gesucht wird nur noch nach dem, wofür sich jemand interessiert.
    """
    from django.db.models import Q

    if household is not None:
        used = (
            Q(shopping_items__shopping_list__household=household)
            | Q(ingredient_recipes__recipe__household=household)
            | Q(inventory_items__household=household)
        )
    else:
        used = (
            Q(shopping_items__isnull=False)
            | Q(ingredient_recipes__isnull=False)
            | Q(inventory_items__isnull=False)
        )
    names = set(Ingredient.objects.filter(used).values_list("name", flat=True).distinct())
    return names


def favorite_product_names(household=None):
    """Favoriten aus den Einstellungen ("Das kaufe ich regelmäßig") – von allen
    Haushaltsmitgliedern bzw. ohne Haushalt von allen Nutzern."""
    from user_settings.models import UserSettings

    settings_qs = UserSettings.objects.all()
    if household is not None:
        settings_qs = settings_qs.filter(user__households=household)
    return {name for names in settings_qs.values_list("favorite_products", flat=True) for name in names or []}


def build_search_terms(household=None):
    terms = {search_name(name) for name in used_ingredient_names(household)}
    terms.update(search_name(name) for name in favorite_product_names(household))

    if household is None:
        # Ohne konkreten Haushalt (z.B. Cron/Command): zusätzlich gängige Produkte
        terms.update(p.lower().strip() for p in COMMON_PRODUCTS)

    return sorted(term for term in terms if len(term) >= 3)


class SyncAlreadyRunning(Exception):
    pass


def _report_progress(source):
    def report(done, total):
        DealSource.objects.filter(pk=source.pk).update(sync_done=done, sync_total=total)
    return report


def sync_marktguru(zip_code=None, limit=50, search_terms=None, keep_old=False, household=None):
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
        DealSource.objects.filter(pk=source.pk).update(sync_done=0, sync_total=0)
        imported_deals = provider.fetch_deals(
            search_terms=search_terms if search_terms is not None else build_search_terms(household),
            limit=limit,
            on_progress=_report_progress(source),
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
                    "product_name": imported.product_name,
                    "description": imported.description,
                    "reference_price": imported.reference_price,
                    "reference_unit": imported.reference_unit,
                    "package_size": imported.package_size,
                    "requires_loyalty": imported.requires_loyalty,
                    "source_categories": imported.source_categories,
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
        DealSource.objects.filter(pk=source.pk).update(last_sync_count=saved_count)
        return saved_count
    except Exception as error:
        release_sync(source, error=error)
        raise