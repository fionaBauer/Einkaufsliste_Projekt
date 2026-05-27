from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import UserSettingsForm
from .models import UserSettings
from deals.sync import sync_marktguru


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            settings_obj = form.save()

            sync_marktguru(settings_obj.postal_code)

            return redirect("user_settings:settings")
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, "user_settings/settings.html", {
        "form": form,
    })