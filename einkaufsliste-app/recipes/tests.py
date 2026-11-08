import json
import tempfile
from datetime import timedelta
from unittest.mock import patch

from yt_dlp.utils import DownloadError

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from deals.models import Deal, DealSource, Store
from households.models import Household
from ingredients.models import Ingredient, IngredientCategory, Unit

from .filters import ingredient_terms
from .models import Recipe, RecipeIngredient, Tag
from .services.reclip.pipeline import process_url
from .services.reclip.video_extractor import _cookie_options, _get_ffmpeg_location
from .services.reclip.web_extractor import _parse_iso_duration, _total_minutes


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
        self.assertContains(detail, 'id="pane-deals"')


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


class RecipeCookingTimeTests(RecipeTestCase):
    def post(self, url, **data):
        return self.client.post(url, data, headers={"X-Requested-With": "XMLHttpRequest"})

    def test_labels(self):
        cases = {None: "", 45: "45 Min.", 60: "1 Std.", 75: "1 Std. 15 Min."}
        for minutes, label in cases.items():
            self.assertEqual(Recipe(cooking_minutes=minutes).cooking_time_label, label)

    def test_manual_create_and_edit(self):
        self.post(reverse("recipes:recipe_create"), name="Curry", servings=2, cooking_minutes=40)
        recipe = Recipe.objects.get(name="Curry")
        self.assertEqual(recipe.cooking_minutes, 40)

        self.post(reverse("recipes:recipe_edit", args=[recipe.pk]), name="Curry", servings=2, cooking_minutes="")
        recipe.refresh_from_db()
        self.assertIsNone(recipe.cooking_minutes)

    def test_form_rejects_invalid_minutes(self):
        response = self.post(reverse("recipes:recipe_create"), name="Curry", servings=2, cooking_minutes=0)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Recipe.objects.exists())

    def test_shown_on_list_and_detail(self):
        recipe = self.recipe("Curry")
        Recipe.objects.filter(pk=recipe.pk).update(cooking_minutes=90)

        self.assertContains(self.client.get(reverse("recipes:recipe_list")), "ca. 1 Std. 30 Min.")
        self.assertContains(
            self.client.get(reverse("recipes:recipe_detail", args=[recipe.pk])),
            "ca. 1 Std. 30 Min.",
        )

    def test_import_saves_minutes_and_ignores_garbage(self):
        cases = {"35": 35, 20: 20, "": None, "schnell": None, -5: None, 99999: None}
        for index, (value, expected) in enumerate(cases.items()):
            self.client.post(
                reverse("recipes:recipe_create_from_extracted"),
                json.dumps({"title": f"Import {index}", "cooking_minutes": value, "ingredients": []}),
                content_type="application/json",
            )
            self.assertEqual(Recipe.objects.get(name=f"Import {index}").cooking_minutes, expected)


class RecipeImportTests(TestCase):
    structured_recipe = {
        "title": "Lasagne",
        "ingredients": [{"name": "Hackfleisch"}],
        "steps": [{"instruction": "Schichten und backen"}],
        "tags": ["Italienisch"],
        "cooking_minutes": None,
    }

    @patch("recipes.services.reclip.pipeline.extract_metadata", side_effect=DownloadError("login required"))
    def test_blocked_video_gives_a_readable_error(self, metadata):
        with self.assertLogs("recipes.services.reclip.pipeline", level="WARNING"):
            with self.assertRaisesMessage(ValueError, "Text einfügen"):
                process_url("https://www.instagram.com/reel/abc/")

    def test_ffmpeg_location(self):
        with patch.dict("os.environ", {"FFMPEG_LOCATION": "/custom"}):
            self.assertEqual(_get_ffmpeg_location(), "/custom")

        with patch.dict("os.environ", {"FFMPEG_LOCATION": ""}):
            with patch("shutil.which", return_value="/opt/homebrew/bin/ffmpeg"):
                self.assertEqual(_get_ffmpeg_location(), "/opt/homebrew/bin")
            with patch("shutil.which", return_value=None):
                self.assertEqual(_get_ffmpeg_location(), "/usr/bin")

    def test_cookie_file_is_optional(self):
        with tempfile.NamedTemporaryFile() as cookie_file:
            with patch.dict("os.environ", {"YTDLP_COOKIES_FILE": cookie_file.name}):
                self.assertEqual(_cookie_options(), {"cookiefile": cookie_file.name})

        with patch.dict("os.environ", {"YTDLP_COOKIES_FILE": "/gibt/es/nicht.txt"}):
            self.assertEqual(_cookie_options(), {})

        with patch.dict("os.environ", {"YTDLP_COOKIES_FILE": ""}):
            self.assertEqual(_cookie_options(), {})

    def test_iso_durations(self):
        cases = {
            "PT30M": 30,
            "PT1H30M": 90,
            "P0DT2H0M": 120,
            "P1DT1H": 1500,
            "P0Y0M0DT0H45M0.000S": 45,
            "PT0S": None,
            "30 Minuten": None,
            "": None,
            None: None,
        }
        for value, minutes in cases.items():
            self.assertEqual(_parse_iso_duration(value), minutes, value)

    def test_total_time_wins_over_parts(self):
        self.assertEqual(_total_minutes({"totalTime": "PT1H", "prepTime": "PT5M"}), 60)
        self.assertEqual(_total_minutes({"prepTime": "PT10M", "cookTime": "PT20M"}), 30)
        self.assertIsNone(_total_minutes({}))

    @patch("recipes.services.reclip.pipeline.classify_recipe")
    @patch("recipes.services.reclip.pipeline.extract_recipe_from_webpage")
    def test_structured_page_gets_categories_and_estimated_time(self, extract, classify):
        extract.return_value = dict(self.structured_recipe)
        classify.return_value = {"tags": ["dinner", "meat"], "cooking_minutes": 75}

        recipe = process_url("https://example.com/lasagne")["recipe"]

        self.assertEqual(recipe["tags"], ["dinner", "meat"])
        self.assertEqual(recipe["cooking_minutes"], 75)

    @patch("recipes.services.reclip.pipeline.classify_recipe")
    @patch("recipes.services.reclip.pipeline.extract_recipe_from_webpage")
    def test_time_from_page_beats_estimate(self, extract, classify):
        extract.return_value = {**self.structured_recipe, "cooking_minutes": 50}
        classify.return_value = {"tags": [], "cooking_minutes": 75}

        self.assertEqual(process_url("https://example.com/lasagne")["recipe"]["cooking_minutes"], 50)

    @patch("recipes.services.reclip.pipeline.classify_recipe", side_effect=RuntimeError("API weg"))
    @patch("recipes.services.reclip.pipeline.extract_recipe_from_webpage")
    def test_import_survives_failed_classification(self, extract, classify):
        extract.return_value = {**self.structured_recipe, "cooking_minutes": 50}

        with self.assertLogs("recipes.services.reclip.pipeline", level="ERROR"):
            recipe = process_url("https://example.com/lasagne")["recipe"]

        self.assertEqual(recipe["title"], "Lasagne")
        self.assertEqual(recipe["cooking_minutes"], 50)
