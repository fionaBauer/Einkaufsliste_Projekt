from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import JsonResponse

from .models import Recipe, RecipeIngredient
from .forms import RecipeForm, RecipeIngredientForm


class RecipeListView(ListView):
    model = Recipe
    template_name = "recipes/recipe_list.html"
    context_object_name = "recipes"
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.GET.get("search", "").strip()
        sort = self.request.GET.get("sort", "name")

        if search:
            queryset = queryset.filter(name__icontains=search)

        allowed_sort_fields = {
            "name": "name",
            "-name": "-name",
            "created_at": "created_at",
            "-created_at": "-created_at",
        }

        return queryset.order_by(allowed_sort_fields.get(sort, "name"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("search", "")
        context["sort"] = self.request.GET.get("sort", "name")
        context["form"] = RecipeForm()
        return context


class RecipeDetailView(DetailView):
    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ingredient_form"] = RecipeIngredientForm()
        return context

    def get_queryset(self):
        return Recipe.objects.prefetch_related("recipe_ingredients__ingredient")


class RecipeCreateView(CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/partials/recipe_form.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self.render_to_response(self.get_context_data(form=form), status=400)
        return super().form_invalid(form)


class RecipeUpdateView(UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/partials/recipe_form.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self.render_to_response(self.get_context_data(form=form), status=400)
        return super().form_invalid(form)


class RecipeDeleteView(DeleteView):
    model = Recipe
    template_name = "recipes/partials/recipe_confirm_delete.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return redirect(self.success_url)


class RecipeIngredientCreateView(CreateView):
    model = RecipeIngredient
    form_class = RecipeIngredientForm
    template_name = "recipes/partials/recipeingredient_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.recipe = get_object_or_404(Recipe, pk=kwargs["recipe_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.recipe = self.recipe
        self.object = form.save()

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self.render_to_response(self.get_context_data(form=form), status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("recipes:recipe_detail", kwargs={"pk": self.recipe.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe"] = self.recipe
        return context


class RecipeIngredientUpdateView(UpdateView):
    model = RecipeIngredient
    form_class = RecipeIngredientForm
    template_name = "recipes/partials/recipeingredient_form.html"
    context_object_name = "recipe_ingredient"

    def form_valid(self, form):
        self.object = form.save()

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self.render_to_response(self.get_context_data(form=form), status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("recipes:recipe_detail", kwargs={"pk": self.object.recipe.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe"] = self.object.recipe
        return context


class RecipeIngredientDeleteView(DeleteView):
    model = RecipeIngredient
    template_name = "recipes/partials/recipeingredient_confirm_delete.html"
    context_object_name = "recipe_ingredient"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        recipe_pk = self.object.recipe.pk
        self.object.delete()

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return redirect("recipes:recipe_detail", pk=recipe_pk)