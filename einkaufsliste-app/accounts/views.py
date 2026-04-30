from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def profile(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        error = None

        if not username:
            error = "Benutzername darf nicht leer sein."
        elif username != request.user.username and User.objects.filter(username=username).exists():
            error = "Dieser Benutzername ist bereits vergeben."
        elif not email:
            error = "E-Mail-Adresse darf nicht leer sein."
        elif email != request.user.email and User.objects.filter(email=email).exists():
            error = "Diese E-Mail-Adresse wird bereits verwendet."

        if error:
            return render(request, "accounts/profile.html", {"error": error})

        request.user.username = username
        request.user.email = email
        request.user.save(update_fields=["username", "email"])
        messages.success(request, "Profil gespeichert.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html")
