import json
import re
from difflib import SequenceMatcher
from fractions import Fraction

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import JsonResponse

from decimal import Decimal, InvalidOperation
from ingredients.models import Ingredient, Unit

from .models import Recipe, RecipeIngredient
from .forms import RecipeForm, RecipeIngredientForm
from .services.reclip.pipeline import process_url

import os
import shutil


class RecipeListView(LoginRequiredMixin, ListView):
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


class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ingredient_form"] = RecipeIngredientForm()
        return context

    def get_queryset(self):
        return Recipe.objects.prefetch_related("recipe_ingredients__ingredient")


class RecipeCreateView(LoginRequiredMixin, CreateView):
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


class RecipeUpdateView(LoginRequiredMixin, UpdateView):
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


class RecipeDeleteView(LoginRequiredMixin, DeleteView):
    model = Recipe
    template_name = "recipes/partials/recipe_confirm_delete.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return redirect(self.success_url)


class RecipeIngredientCreateView(LoginRequiredMixin, CreateView):
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


class RecipeIngredientUpdateView(LoginRequiredMixin, UpdateView):
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


class RecipeIngredientDeleteView(LoginRequiredMixin, DeleteView):
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
    
@login_required
@require_POST
def extract_recipe_from_link(request):
    try:
        data = json.loads(request.body)
        url = data.get("url", "").strip()

        if not url:
            return JsonResponse(
                {"success": False, "error": "Bitte gib einen Link ein."},
                status=400,
            )

        result = process_url(url)

        return JsonResponse({
            "success": True,
            "recipe": result["recipe"],
            "raw_transcript": result["raw_transcript"],
            "raw_caption": result["raw_caption"],
        })

    except ValueError as error:
        return JsonResponse(
            {"success": False, "error": str(error)},
            status=422,
        )
    except Exception as error:
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "error": f"Extraktion fehlgeschlagen: {str(error)}"},
            status=500,
        )
    
@login_required
@require_POST
def create_recipe_from_extracted_data(request):
    try:
        data = json.loads(request.body)

        title = (data.get("title") or "").strip()
        servings = data.get("servings")
        instructions = data.get("instructions") or ""
        ingredients_data = data.get("ingredients") or []

        if not title:
            return JsonResponse(
                {"success": False, "error": "Rezeptname fehlt."},
                status=400,
            )

        try:
            servings = int(servings) if servings else 1
        except (TypeError, ValueError):
            servings = 1

        recipe = Recipe.objects.create(
            name=title,
            servings=max(servings, 1),
            instructions=instructions.strip(),
        )

        merged_recipe_ingredients = {}

        for item in ingredients_data:
            ingredient_name = (item.get("name") or "").strip()
            if not ingredient_name:
                continue

            parsed = _parse_amount_and_unit(
                amount=item.get("amount"),
                unit=item.get("unit"),
            )

            quantity = parsed["quantity"]
            unit = parsed["unit"]
            notes = (item.get("notes") or "").strip()

            ingredient = _get_or_create_matching_ingredient(
                ingredient_name=ingredient_name,
                default_unit=unit or Unit.GRAM,
            )

            final_quantity = quantity if quantity is not None else Decimal("1.00")
            final_unit = unit or ingredient.default_unit

            key = ingredient.id

            if key in merged_recipe_ingredients:
                existing = merged_recipe_ingredients[key]

                merged_quantity, merged_unit = _merge_quantities_with_units(
                    existing_quantity=existing["quantity"],
                    existing_unit=existing["unit"],
                    new_quantity=final_quantity,
                    new_unit=final_unit,
                )

                existing["quantity"] = merged_quantity
                existing["unit"] = merged_unit

                if notes:
                    existing_notes = existing["notes"].strip()
                    if existing_notes:
                        note_parts = {part.strip() for part in existing_notes.split(",") if part.strip()}
                        note_parts.add(notes)
                        existing["notes"] = ", ".join(sorted(note_parts))
                    else:
                        existing["notes"] = notes
            else:
                merged_recipe_ingredients[key] = {
                    "ingredient": ingredient,
                    "quantity": final_quantity,
                    "unit": final_unit,
                    "notes": notes,
                }

        for merged_item in merged_recipe_ingredients.values():
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=merged_item["ingredient"],
                quantity=merged_item["quantity"],
                unit=merged_item["unit"],
                notes=merged_item["notes"],
            )

        return JsonResponse({
            "success": True,
            "recipe_id": recipe.id,
            "redirect_url": reverse("recipes:recipe_detail", kwargs={"pk": recipe.pk}),
        })

    except Exception as error:
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "error": f"Speichern fehlgeschlagen: {str(error)}"},
            status=500,
        )


def _parse_amount_and_unit(amount, unit):
    raw_amount = "" if amount is None else str(amount).strip()
    raw_unit = "" if unit is None else str(unit).strip().lower()

    quantity = _parse_decimal_amount(raw_amount)
    mapped_unit = _map_unit(raw_unit)

    if quantity is not None:
        return {
            "quantity": quantity,
            "unit": mapped_unit,
        }

    combined = f"{raw_amount} {raw_unit}".strip()
    quantity, extracted_unit = _extract_quantity_and_unit_from_text(combined)

    return {
        "quantity": quantity,
        "unit": extracted_unit or mapped_unit,
    }


def _parse_decimal_amount(value):
    if value in (None, "", "null"):
        return None

    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    value = str(value).strip().lower()
    value = value.replace(",", ".")

    if "-" in value:
        value = value.split("-")[0].strip()

    try:
        return Decimal(value)
    except InvalidOperation:
        pass

    try:
        return Decimal(str(float(Fraction(value))))
    except (ValueError, ZeroDivisionError):
        return None


def _extract_quantity_and_unit_from_text(text):
    if not text:
        return None, ""

    normalized = text.strip().lower()
    normalized = normalized.replace(",", ".")
    normalized = normalized.replace("esslöffel", "el")
    normalized = normalized.replace("essloeffel", "el")
    normalized = normalized.replace("el.", "el")
    normalized = normalized.replace("teelöffel", "tl")
    normalized = normalized.replace("teeloeffel", "tl")
    normalized = normalized.replace("tl.", "tl")

    pattern = r"(?P<amount>\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*(?P<unit>[a-zA-ZäöüÄÖÜ\.]+)?"
    match = re.search(pattern, normalized)

    if not match:
        return None, ""

    raw_amount = (match.group("amount") or "").strip()
    raw_unit = (match.group("unit") or "").strip().lower()

    quantity = _parse_decimal_amount(raw_amount)
    unit = _map_unit(raw_unit)

    return quantity, unit


def _map_unit(raw_unit):
    unit_map = {
        "g": Unit.GRAM,
        "gramm": Unit.GRAM,
        "gram": Unit.GRAM,

        "kg": Unit.KILOGRAM,
        "kilogramm": Unit.KILOGRAM,
        "kilogram": Unit.KILOGRAM,

        "ml": Unit.MILLILITER,
        "milliliter": Unit.MILLILITER,

        "l": Unit.LITER,
        "liter": Unit.LITER,

        "pcs": Unit.PIECE,
        "stück": Unit.PIECE,
        "stueck": Unit.PIECE,
        "stücke": Unit.PIECE,
        "stuecke": Unit.PIECE,
        "piece": Unit.PIECE,
        "pieces": Unit.PIECE,

        "el": Unit.TABLESPOON,
        "esslöffel": Unit.TABLESPOON,
        "essloeffel": Unit.TABLESPOON,
        "tbsp": Unit.TABLESPOON,
        "tablespoon": Unit.TABLESPOON,
        "tablespoons": Unit.TABLESPOON,

        "tl": Unit.TEASPOON,
        "teelöffel": Unit.TEASPOON,
        "teeloeffel": Unit.TEASPOON,
        "tsp": Unit.TEASPOON,
        "teaspoon": Unit.TEASPOON,
        "teaspoons": Unit.TEASPOON,
    }

    return unit_map.get((raw_unit or "").strip().lower(), "")

def _normalize_ingredient_name(name: str) -> str:
    if not name:
        return ""

    name = name.strip().lower()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Klammern und Sonderzeichen raus
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # häufige Beschreibungswörter entfernen
    stopwords = {
        "frisch", "klein", "kleine", "kleiner", "gross", "grosse", "große", "großer",
        "gehackt", "gewuerfelt", "gewürfelt", "fein", "bio", "optional",
    }

    parts = [part for part in name.split() if part not in stopwords]

    # sehr einfache Singularisierung
    normalized_parts = []
    for part in parts:
        if part.endswith("en") and len(part) > 4:
            normalized_parts.append(part[:-2])
        elif part.endswith("e") and len(part) > 4:
            normalized_parts.append(part[:-1])
        elif part.endswith("s") and len(part) > 4:
            normalized_parts.append(part[:-1])
        else:
            normalized_parts.append(part)

    normalized = " ".join(normalized_parts)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def _find_similar_ingredient(ingredient_name: str):
    normalized_target = _normalize_ingredient_name(ingredient_name)
    if not normalized_target:
        return None

    ingredients = Ingredient.objects.all()

    best_match = None
    best_score = 0.0

    for ingredient in ingredients:
        normalized_existing = _normalize_ingredient_name(ingredient.name)

        if normalized_existing == normalized_target:
            return ingredient

        score = SequenceMatcher(None, normalized_target, normalized_existing).ratio()

        if score > best_score:
            best_score = score
            best_match = ingredient

    if best_score >= 0.88:
        return best_match

    return None


def _get_or_create_matching_ingredient(ingredient_name: str, default_unit: str):
    # 1. exakte Suche
    exact_match = Ingredient.objects.filter(name__iexact=ingredient_name).first()
    if exact_match:
        return exact_match

    # 2. ähnliche Suche auf normalisiertem Namen
    similar_match = _find_similar_ingredient(ingredient_name)
    if similar_match:
        return similar_match

    # 3. neu anlegen
    try:
        return Ingredient.objects.create(
            name=ingredient_name.strip(),
            default_unit=default_unit or Unit.GRAM,
        )
    except Exception:
        # Falls parallel / wegen Unique doch schon vorhanden
        existing = Ingredient.objects.filter(name__iexact=ingredient_name.strip()).first()
        if existing:
            return existing
        raise

def _to_base_unit(quantity, unit):
    if quantity is None:
        return None, unit

    if unit == Unit.KILOGRAM:
        return quantity * Decimal("1000"), Unit.GRAM

    if unit == Unit.LITER:
        return quantity * Decimal("1000"), Unit.MILLILITER

    return quantity, unit


def _from_base_unit(quantity, unit):
    if quantity is None:
        return None, unit

    if unit == Unit.GRAM and quantity >= Decimal("1000"):
        return quantity / Decimal("1000"), Unit.KILOGRAM

    if unit == Unit.MILLILITER and quantity >= Decimal("1000"):
        return quantity / Decimal("1000"), Unit.LITER

    return quantity, unit


def _merge_quantities_with_units(existing_quantity, existing_unit, new_quantity, new_unit):
    existing_base_quantity, existing_base_unit = _to_base_unit(existing_quantity, existing_unit)
    new_base_quantity, new_base_unit = _to_base_unit(new_quantity, new_unit)

    if existing_base_unit == new_base_unit:
        merged_base_quantity = existing_base_quantity + new_base_quantity
        return _from_base_unit(merged_base_quantity, existing_base_unit)

    # Falls Einheiten nicht kompatibel sind, alte Werte beibehalten
    # statt kaputt zu mergen.
    return existing_quantity, existing_unit

@login_required
def ffmpeg_debug(request):
    return JsonResponse({
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "PATH": os.environ.get("PATH", ""),
        "FFMPEG_LOCATION": os.environ.get("FFMPEG_LOCATION", ""),
    })