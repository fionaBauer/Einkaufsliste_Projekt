import threading

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Store
from .services import get_active_deals
from .sync import sync_marktguru


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

    try:
        thread = threading.Thread(
            target=sync_marktguru,
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