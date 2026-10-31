import logging
import threading

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import DealSource, Store
from .services import get_active_deals
from .sync import sync_marktguru, SyncAlreadyRunning, STALE_SYNC_LOCK_AFTER
from .providers.marktguru import MarktguruProvider

logger = logging.getLogger(__name__)


def _sync_marktguru_in_background(zip_code):
    """Wird in einem eigenen Thread ausgefuehrt - Exceptions hier wuerden sonst
    komplett unbemerkt verschwinden, da die Response laengst zurueckgegangen ist."""
    try:
        sync_marktguru(zip_code)
    except SyncAlreadyRunning:
        pass  # erwarteter Fall (Doppelklick o.ae.), kein echter Fehler
    except Exception:
        logger.exception("MarktGuru-Sync fehlgeschlagen (PLZ %s)", zip_code)
    finally:
        close_old_connections()


@login_required
def deal_list(request):
    search = request.GET.get("search", "").strip()
    store_id = request.GET.get("store", "").strip()

    deals = get_active_deals()

    if search:
        deals = deals.filter(title__icontains=search)

    if store_id:
        deals = deals.filter(store_id=store_id)

    stores = Store.objects.order_by("name")

    return render(request, "deals/deal_list.html", {
        "deals": deals,
        "stores": stores,
        "search": search,
        "selected_store": store_id,
    })


@login_required
def sync_deals_view(request):
    if request.method != "POST":
        return redirect("deals:list")

    settings_obj = getattr(request.user, "settings", None)

    if not settings_obj or not settings_obj.postal_code:
        messages.error(request, "Bitte speichere zuerst deine Postleitzahl.")
        return redirect("user_settings:settings")

    zip_code = settings_obj.postal_code

    # Nur ein optimistischer Hinweis fuer sofortiges Feedback - die eigentliche,
    # race-sichere Pruefung passiert atomar in sync_marktguru() selbst.
    stale_cutoff = timezone.now() - STALE_SYNC_LOCK_AFTER
    already_running = DealSource.objects.filter(
        name=MarktguruProvider.source_name,
        is_syncing=True,
        sync_started_at__gte=stale_cutoff,
    ).exists()

    if already_running:
        messages.info(request, "Es läuft bereits eine Aktualisierung der Rabatte im Hintergrund.")
        return redirect("deals:list")

    try:
        thread = threading.Thread(
            target=_sync_marktguru_in_background,
            args=(zip_code,),
            daemon=True,
        )
        thread.start()

        messages.success(
            request,
            "Rabatte werden jetzt im Hintergrund aktualisiert."
        )
    except Exception as error:
        messages.error(request, f"Rabatte konnten nicht geladen werden: {error}")

    return redirect("deals:list")