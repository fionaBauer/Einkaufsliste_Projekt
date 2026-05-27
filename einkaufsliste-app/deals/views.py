from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Store
from .services import get_active_deals


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