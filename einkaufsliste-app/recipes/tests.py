import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from deals.models import Deal, DealSource, Store
from households.models import Household
from ingredients.models import Ingredient, IngredientCategory, Unit

from .filters import ingredient_terms
from .models import Recipe, RecipeIngredient, Tag


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class RecipeTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("fiona", "fiona@example.com", "pw")
        self.household = Household.objects.create(name="Zuhause", created_by=self.user)
        self.household.members.add(self.user)
        self.client.force_login(self.user)

    def recipe(self, name, tags=(), ingredients=(), household=None):
        recipe = Recipe.objects.create(household=household or self.household, name=name)
        recipe.set_tags([tag.value for tag in tags])
        for ingredient_name in ingredients:
            ingredient, _ = Ingredient.objects.get_or_create(name=ingredient_name)
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=1, unit=Unit.PIECE)
        return recipe

    def names(self, query=""):
        response = self.client.get(reverse("recipes:recipe_list") + query)
        self.assertEqual(response.status_code, 200)
        return [recipe.name for recipe in response.context["recipes"]]


class RecipeFilterTests(RecipeTestCase):
    def test_tags_in_one_group_match_any(self):
        self.recipe("Porridge", [Tag.BREAKFAST])
        self.recipe("Curry", [Tag.DINNER])
        self.recipe("Kuchen", [Tag.CAKE])

        self.assertEqual(self.names("?tag=breakfast&tag=dinner"), ["Curry", "Porridge"])

    def test_tags_across_groups_must_all_match(self):
        self.recipe("Linsensuppe", [Tag.DINNER, Tag.SOUP])
        self.recipe("Curry", [Tag.DINNER, Tag.MAIN])
        self.recipe("Tomatensuppe", [Tag.LUNCH, Tag.SOUP])

        self.assertEqual(self.names("?tag=dinner&tag=soup"), ["Linsensuppe"])

    def test_special_tags_must_all_match(self):
        self.recipe("Beides", [Tag.GLUTEN_FREE, Tag.LACTOSE_FREE])
        self.recipe("Nur glutenfrei", [Tag.GLUTEN_FREE])

        self.assertEqual(self.names("?tag=gluten_free&tag=lactose_free"), ["Beides"])

    def test_vegetarian_includes_vegan(self):
        self.recipe("Vegan", [Tag.VEGAN])
        self.recipe("Veggie", [Tag.VEGETARIAN])
        self.recipe("Steak", [Tag.MEAT])

        self.assertEqual(self.names("?tag=vegetarian"), ["Vegan", "Veggie"])
        self.assertEqual(self.names("?tag=vegan"), ["Vegan"])

    def test_multiple_ingredients_must_all_match(self):
        self.recipe("Reispfanne", ingredients=["Hähnchenbrustfilet", "Basmatireis"])
        self.recipe("Salat", ingredients=["Hähnchenbrustfilet"])

        self.assertEqual(self.names("?ingredient=Hähnchen&ingredient=Reis"), ["Reispfanne"])

    def test_ingredient_synonyms(self):
        self.recipe("Hähnchenpfanne", ingredients=["Hähnchenbrustfilet"])
        self.recipe("Carbonara", ingredients=["Spaghetti"])
        self.recipe("Bolognese", ingredients=["Penne"])

        self.assertEqual(self.names("?ingredient=Hühnchen"), ["Hähnchenpfanne"])
        self.assertEqual(self.names("?ingredient=Nudeln"), ["Bolognese", "Carbonara"])
        self.assertEqual(self.names("?ingredient=Spaghetti"), ["Carbonara"])

    def test_specific_term_is_not_widened(self):
        self.assertEqual(ingredient_terms("Hähnchenbrust"), ["hähnchenbrust"])

    def test_search_finds_names_and_ingredients_without_duplicates(self):
        self.recipe("Reispfanne", ingredients=["Basmatireis", "Reisessig"])
        self.recipe("Milchreis")
        self.recipe("Salat")

        self.assertEqual(self.names("?search=reis"), ["Milchreis", "Reispfanne"])

    def test_sort_and_invalid_values(self):
        self.recipe("A")
        self.recipe("B")

        self.assertEqual(self.names("?sort=-name"), ["B", "A"])
        self.assertEqual(self.names("?sort=password&tag=gibtsnicht"), ["A", "B"])

    def test_other_households_stay_hidden(self):
        other = Household.objects.create(name="Andere")
        self.recipe("Fremd", [Tag.DINNER], ["Geheimzutat"], household=other)

        self.assertEqual(self.names("?tag=dinner"), [])
        response = self.client.get(reverse("recipes:recipe_list"))
        self.assertNotContains(response, "Geheimzutat")

    def test_chip_removes_only_its_own_filter(self):
        self.recipe("Curry", [Tag.DINNER, Tag.MAIN])
        response = self.client.get(reverse("recipes:recipe_list") + "?tag=dinner&tag=main&ingredient=Reis")

        chips = {chip["label"]: chip["query"] for chip in response.context["filters"].chips()}
        self.assertEqual(chips["Abendessen"], "tag=main&ingredient=Reis")
        self.assertEqual(chips["Reis"], "tag=dinner&tag=main")
        self.assertEqual(response.context["filters"].active_count, 3)


class RecipeDealTests(RecipeTestCase):
    def setUp(self):
        super().setUp()
        self.milk = Ingredient.objects.create(name="Milch", category=IngredientCategory.DAIRY)
        source = DealSource.objects.create(name="Test")
        store = Store.objects.create(name="Lidl")
        for price in (1, 2):
            Deal.objects.create(
                source=source, store=store, external_id=str(price), title="Milch", product_name="Milch", deal_price=price,
                valid_until=timezone.now().date() + timedelta(days=3),
            )

    def test_badge_counts_and_filter(self):
        with_deal = self.recipe("Milchreis", ingredients=["Milch"])
        self.recipe("Salat")

        response = self.client.get(reverse("recipes:recipe_list"))
        counts = {recipe.name: recipe.deal_count for recipe in response.context["recipes"]}
        self.assertEqual(counts, {"Milchreis": 2, "Salat": 0})
        self.assertContains(response, "2 Rabatte")
        self.assertNotContains(response, "Passend zu aktuellen Rabatten")

        self.assertEqual(self.names("?deals=1"), ["Milchreis"])

        detail = self.client.get(reverse("recipes:recipe_detail", args=[with_deal.pk]))
        self.assertEqual(len(detail.context["deals"]), 2)
        self.assertContains(detail, "Aktuelle Rabatte")


class RecipeTagEditingTests(RecipeTestCase):
    def post(self, url, **data):
        return self.client.post(url, data, headers={"X-Requested-With": "XMLHttpRequest"})

    def test_create_with_tags(self):
        response = self.post(
            reverse("recipes:recipe_create"),
            name="Suppe", servings=2, tags_course=["soup"], tags_special=["quick", "low_carb"],
        )

        self.assertEqual(response.status_code, 200)
        recipe = Recipe.objects.get(name="Suppe")
        self.assertEqual(recipe.tag_labels, ["Suppe", "Low Carb", "Schnell"])

    def test_edit_shows_saved_tags_and_replaces_them(self):
        recipe = self.recipe("Suppe", [Tag.SOUP, Tag.LUNCH])
        url = reverse("recipes:recipe_edit", args=[recipe.pk])

        form = self.client.get(url).context["form"]
        self.assertEqual(form["tags_course"].value(), ["soup"])
        self.assertEqual(form["tags_meal"].value(), ["lunch"])

        self.post(url, name="Suppe", servings=1, tags_meal=["dinner"])
        self.assertEqual(recipe.tag_labels, ["Abendessen"])

    def test_detail_shows_tags(self):
        recipe = self.recipe("Suppe", [Tag.SOUP])
        response = self.client.get(reverse("recipes:recipe_detail", args=[recipe.pk]))
        self.assertContains(response, '<li class="recipe-tag">Suppe</li>', html=True)

    def test_import_saves_only_known_tags(self):
        response = self.client.post(
            reverse("recipes:recipe_create_from_extracted"),
            json.dumps({"title": "Import", "servings": 2, "tags": ["soup", "italienisch"], "ingredients": []}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recipe.objects.get(name="Import").tag_labels, ["Suppe"])
