from accounts.forms import RegisterForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from recipes.models import Recipe


@login_required
def home(request):
    household = request.user.households.first()
    recent_recipes = Recipe.objects.filter(household=household).order_by("-created_at")[:5]
    return render(request, "core/home.html", {"recent_recipes": recent_recipes})


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("households:create")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})