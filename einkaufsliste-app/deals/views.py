import logging
import threading
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.shortcuts import redirect
from django.utils import timezone

from households.models import Household

from .models import DealSource
from .services import get_active_deals
from .sync import sync_marktguru, SyncAlreadyRunning, STALE_SYNC_LOCK_AFTER
from .providers.marktguru import MarktguruProvider

logger = logging.getLogger(__name__)

# Angebote gelten als veraltet → beim Öffnen von Startseite/Einkaufsliste im Hintergrund neu laden
AUTO_REFRESH_AFTER = timedelta(hours=24)
# Nach einem Fehlversuch nicht bei jedem Live-Update (alle 15 s) erneut starten
AUTO_RETRY_AFTER = timedelta(minutes=30)
BERLIN = ZoneInfo("Europe/Berlin")


def _sync_marktguru_in_background(zip_code, household_id=None):
    """Wird in einem eigenen Thread ausgefuehrt - Exceptions hier wuerden sonst
    komplett unbemerkt verschwinden, da die Response laengst zurueckgegangen ist."""
    try:
        household = Household.objects.filter(pk=household_id).first() if household_id else None
        sync_marktguru(zip_code, household=household)
    except SyncAlreadyRunning:
        pass  # erwarteter Fall (Doppelklick o.ae.), kein echter Fehler
    except Exception:
        logger.exception("MarktGuru-Sync fehlgeschlagen (PLZ %s)", zip_code)
    finally:
        close_old_connections()


def _get_source():
    return DealSource.objects.filter(name=MarktguruProvider.source_name).first()


def _is_syncing(source):
    if not source or not source.is_syncing:
        return False
    return bool(source.sync_started_at) and source.sync_started_at >= timezone.now() - STALE_SYNC_LOCK_AFTER


def _postal_code(user):
    from user_settings.models import UserSettings

    return UserSettings.objects.filter(user=user).values_list("postal_code", flat=True).first() or ""


def start_deal_sync(user):
    """Startet das Laden der Angebote für die PLZ des Nutzers im Hintergrund."""
    zip_code = _postal_code(user)
    if not zip_code:
        return False
    household = user.households.first()
    threading.Thread(
        target=_sync_marktguru_in_background,
        args=(zip_code, household.pk if household else None),
        daemon=True,
    ).start()
    return True


def refresh_deals_if_stale(user):
    """Lädt die Angebote neu, wenn sie älter als einen Tag sind oder alle abgelaufen.

    Gibt es keine eigene Rabatt-Seite mehr, passiert das beim Öffnen von Startseite und
    Einkaufsliste – ohne Ladeanzeige, das Live-Update holt die neuen Angebote nach.
    """
    if not _postal_code(user):
        return
    source = _get_source()
    now = timezone.now()
    if _is_syncing(source):
        return
    if source and source.sync_started_at and source.sync_started_at > now - AUTO_RETRY_AFTER:
        return
    is_stale = (
        not source
        or not source.last_synced_at
        or source.last_synced_at < now - AUTO_REFRESH_AFTER
        or not get_active_deals().exists()
    )
    if is_stale:
        start_deal_sync(user)


def deals_status_label():
    """Für die Einstellungen: "heute, 08:12 Uhr" / "wird gerade geladen …"."""
    source = _get_source()
    if _is_syncing(source):
        return "Angebote werden gerade geladen …"
    if not source or not source.last_synced_at:
        return "Noch keine Angebote geladen"
    local = source.last_synced_at.astimezone(BERLIN)
    today = timezone.now().astimezone(BERLIN).date()
    if local.date() == today:
        when = f"heute, {local:%H:%M} Uhr"
    elif local.date() == today - timedelta(days=1):
        when = f"gestern, {local:%H:%M} Uhr"
    else:
        when = f"{local:%d.%m.}, {local:%H:%M} Uhr"
    return f"Stand: {when}"


@login_required
def sync_deals_view(request):
    if request.method != "POST":
        return redirect("user_settings:settings")

    if not _postal_code(request.user):
        messages.error(request, "Bitte speichere zuerst deine Postleitzahl.")
        return redirect("user_settings:settings")

    # Nur ein optimistischer Hinweis - die race-sichere Pruefung passiert atomar in sync_marktguru().
    if _is_syncing(_get_source()):
        messages.info(request, "Die Angebote werden bereits geladen.")
        return redirect("user_settings:settings")

    try:
        start_deal_sync(request.user)
    except Exception as error:
        messages.error(request, f"Angebote konnten nicht geladen werden: {error}")
        return redirect("user_settings:settings")

    messages.success(request, "Angebote werden im Hintergrund geladen.")
    return redirect("user_settings:settings")
