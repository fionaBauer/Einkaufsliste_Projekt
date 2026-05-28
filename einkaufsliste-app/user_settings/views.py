from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import UserSettingsForm
from .models import UserSettings


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            return redirect("user_settings:settings")
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, "user_settings/settings.html", {
        "form": form,
    })