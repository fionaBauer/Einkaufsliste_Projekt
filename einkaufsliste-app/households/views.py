from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Household


@login_required
def household_create(request):
    if request.user.households.exists():
        return redirect("households:detail")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            household = Household.objects.create(
                name=name,
                created_by=request.user,
            )
            household.members.add(request.user)
            return redirect("home")

    return render(request, "households/household_create.html")


@login_required
def household_detail(request):
    household = request.user.households.first()
    if not household:
        return redirect("households:create")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "regenerate_token":
            household.regenerate_invite_token()
        elif action == "rename":
            name = request.POST.get("name", "").strip()
            if name:
                household.name = name
                household.save(update_fields=["name"])
        elif action == "leave":
            household.members.remove(request.user)
            return redirect("households:create")

    return render(request, "households/household_detail.html", {"household": household})


@login_required
def household_join(request, token):
    household = get_object_or_404(Household, invite_token=token)

    if request.user.households.exists():
        current = request.user.households.first()
        if current == household:
            return redirect("households:detail")
        return render(request, "households/household_join.html", {
            "household": household,
            "already_in_household": True,
        })

    if request.method == "POST":
        household.members.add(request.user)
        return redirect("home")

    return render(request, "households/household_join.html", {
        "household": household,
        "already_in_household": False,
    })
