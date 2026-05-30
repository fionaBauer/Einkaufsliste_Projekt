from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import UserSettingsForm
from .models import UserSettings

User = get_user_model()


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Username speichern
        username = request.POST.get("username", "").strip()
        error = None

        if not username:
            error = "Benutzername darf nicht leer sein."
        elif username != request.user.username and User.objects.filter(username=username).exists():
            error = "Dieser Benutzername ist bereits vergeben."

        if error:
            form = UserSettingsForm(request.POST, instance=settings_obj)
            return render(request, "user_settings/settings.html", {"form": form, "error": error})

        request.user.username = username
        request.user.save(update_fields=["username"])

        # PLZ speichern
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()

        messages.success(request, "Einstellungen gespeichert.")
        return redirect("user_settings:settings")

    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, "user_settings/settings.html", {"form": form})