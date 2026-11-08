from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from households.models import Household
from ingredients.models import Ingredient
from recipes.models import Recipe, RecipeIngredient
from shopping.models import ShoppingList, ShoppingListItem
from user_settings.models import UserSettings
from user_settings.views import parse_favorites

from .models import Deal, DealSource, Store, store_offer_url
from .providers.marktguru import MarktguruProvider
from .services import get_user_deals
from .views import refresh_deals_if_stale


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class DealTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("fiona", "fiona@example.com", "pw")
        self.household = Household.objects.create(name="Zuhause", created_by=self.user)
        self.household.members.add(self.user)
        self.settings, _ = UserSettings.objects.get_or_create(user=self.user)
        self.settings.postal_code = "89231"
        self.settings.save()
        self.client.force_login(self.user)
        # Nie echte Marktguru-Abfragen im Hintergrund starten
        sync_patcher = patch("deals.views._sync_marktguru_in_background")
        sync_patcher.start()
        self.addCleanup(sync_patcher.stop)
        # Frisch geladen → kein automatischer Hintergrund-Sync während der Tests
        self.source = DealSource.objects.create(
            name=MarktguruProvider.source_name, last_synced_at=timezone.now(),
        )

    def deal(self, title, store, price, product_name=None):
        store_obj, _ = Store.objects.get_or_create(name=store)
        return Deal.objects.create(
            source=self.source, store=store_obj, title=title, product_name=product_name or title,
            deal_price=Decimal(price), external_id=f"{store}-{title}",
            valid_until=timezone.now().date() + timedelta(days=3),
        )

    def add_to_list(self, *names):
        shopping_list, _ = ShoppingList.objects.get_or_create(household=self.household)
        for name in names:
            ingredient, _ = Ingredient.objects.get_or_create(name=name)
            ShoppingListItem.objects.create(shopping_list=shopping_list, ingredient=ingredient)
        return shopping_list


class StoreSelectionTests(DealTestCase):
    def test_only_selected_stores(self):
        self.deal("Butter", "Lidl", "1.49")
        self.deal("Butter", "REWE", "1.29")
        self.settings.preferred_stores = ["Lidl"]
        self.settings.save()

        self.assertEqual([d.store.name for d in get_user_deals(self.user)], ["Lidl"])

    def test_no_selection_means_all_stores(self):
        self.deal("Butter", "Lidl", "1.49")
        self.deal("Butter", "REWE", "1.29")

        self.assertEqual(get_user_deals(self.user).count(), 2)

    def test_settings_save_stores_and_favorites(self):
        self.deal("Butter", "Lidl", "1.49")
        with patch("user_settings.views.start_deal_sync") as start:
            self.client.post(reverse("user_settings:deals"), {
                "stores": ["Lidl"], "favorites": "Kaffee, Butter,  kaffee ",
            })
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.preferred_stores, ["Lidl"])
        self.assertEqual(self.settings.favorite_products, ["Kaffee", "Butter"])
        start.assert_called_once()  # neue Favoriten → Angebote dafür nachladen

    def test_settings_overview_summarizes_sections(self):
        self.settings.preferred_stores = ["Lidl", "REWE"]
        self.settings.favorite_products = ["Kaffee"]
        self.settings.save()

        response = self.client.get(reverse("user_settings:settings"))

        self.assertContains(response, "fiona · PLZ 89231")
        self.assertContains(response, "Zuhause · 1 Mitglied")
        self.assertContains(response, "2 Läden · 1 Favorit")

    def test_account_change_postal_code_loads_deals(self):
        with patch("user_settings.views.start_deal_sync") as start:
            self.client.post(reverse("user_settings:account"), {"username": "fiona2", "postal_code": "80331"})
        self.settings.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual((self.user.username, self.settings.postal_code), ("fiona2", "80331"))
        start.assert_called_once()

    def test_account_rejects_taken_username(self):
        get_user_model().objects.create_user("vergeben", "x@example.com", "pw")
        response = self.client.post(reverse("user_settings:account"), {"username": "vergeben", "postal_code": "1"})
        self.assertContains(response, "bereits vergeben")
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.postal_code, "89231")

    def test_parse_favorites(self):
        self.assertEqual(parse_favorites("Kaffee;Butter\nHähnchen, ,Kaffee"), ["Kaffee", "Butter", "Hähnchen"])


class ShoppingListDealTests(DealTestCase):
    def test_best_deal_shown_at_item(self):
        self.deal("Butter", "Lidl", "1.49")
        shopping_list = self.add_to_list("Butter")

        response = self.client.get(reverse("shopping:detail", args=[shopping_list.pk]))

        self.assertContains(response, "shopping-deal")
        self.assertContains(response, "1.49 €")
        self.assertContains(response, 'href="https://www.lidl.de/"')

    def test_group_by_store(self):
        self.deal("Butter", "Lidl", "1.49")
        self.deal("Gurke", "REWE", "0.59")
        self.deal("Milch", "Lidl", "0.99")
        shopping_list = self.add_to_list("Butter", "Gurke", "Milch", "Salz")
        url = reverse("shopping:detail", args=[shopping_list.pk])

        response = self.client.get(url + "?group=store")
        groups = [(g["store"], [i.ingredient.name for i in g["items"]]) for g in response.context["store_groups"]]
        self.assertEqual(groups, [("Lidl", ["Butter", "Milch"]), ("REWE", ["Gurke"]), (None, ["Salz"])])

        # bleibt nach dem nächsten Aufruf (z.B. nach Abhaken) erhalten
        self.assertTrue(self.client.get(url).context["group_by_store"])
        self.assertFalse(self.client.get(url + "?group=list").context["group_by_store"])

    def test_no_switch_without_deals(self):
        shopping_list = self.add_to_list("Salz")
        response = self.client.get(reverse("shopping:detail", args=[shopping_list.pk]))
        self.assertNotContains(response, "view-switch")


class HomeDealTests(DealTestCase):
    def test_favorites_on_sale(self):
        self.deal("Jacobs Kaffee", "Lidl", "4.99", product_name="Kaffee")
        self.settings.favorite_products = ["Kaffee", "Butter"]
        self.settings.save()

        response = self.client.get(reverse("home"))

        self.assertEqual([hit["name"] for hit in response.context["favorite_deals"]], ["Kaffee"])
        self.assertContains(response, "Deine Favoriten im Angebot")

    def test_cheap_recipes_ranked_by_ingredients_on_sale(self):
        self.deal("Hackfleisch", "Lidl", "3.99")
        self.deal("Paprika", "Lidl", "1.29")
        chili = Recipe.objects.create(household=self.household, name="Chili")
        salad = Recipe.objects.create(household=self.household, name="Salat")
        for recipe, names in ((chili, ["Hackfleisch", "Paprika"]), (salad, ["Paprika", "Essig"])):
            for name in names:
                ingredient, _ = Ingredient.objects.get_or_create(name=name)
                RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=1)

        response = self.client.get(reverse("home"))

        cheap = response.context["cheap_recipes"]
        self.assertEqual([s["recipe"].name for s in cheap], ["Chili", "Salat"])
        self.assertEqual(cheap[0]["ingredients"], ["Hackfleisch", "Paprika"])

    def test_favorite_hint_when_none_set(self):
        self.deal("Butter", "Lidl", "1.49")
        self.assertContains(self.client.get(reverse("home")), "Favoriten festlegen")


class AutoRefreshTests(DealTestCase):
    def test_stale_deals_start_sync(self):
        self.deal("Butter", "Lidl", "1.49")
        DealSource.objects.filter(pk=self.source.pk).update(last_synced_at=timezone.now() - timedelta(days=2))
        with patch("deals.views.start_deal_sync") as start:
            refresh_deals_if_stale(self.user)
        start.assert_called_once()

    def test_no_retry_right_after_failed_sync(self):
        DealSource.objects.filter(pk=self.source.pk).update(
            last_synced_at=None, sync_started_at=timezone.now() - timedelta(minutes=5),
        )
        with patch("deals.views.start_deal_sync") as start:
            refresh_deals_if_stale(self.user)
        start.assert_not_called()

    def test_fresh_deals_no_sync(self):
        self.deal("Butter", "Lidl", "1.49")
        with patch("deals.views.start_deal_sync") as start:
            refresh_deals_if_stale(self.user)
        start.assert_not_called()


class StoreLinkTests(TestCase):
    def test_store_names_from_marktguru(self):
        self.assertEqual(store_offer_url("ALDI SÜD"), "https://www.aldi-sued.de/")
        self.assertEqual(store_offer_url("Netto Marken-Discount"), "https://www.netto-online.de/angebote")
        self.assertEqual(store_offer_url("Unbekannter Markt"), "")


class RecipeDetailTabTests(DealTestCase):
    def test_deals_tab_only_with_deals(self):
        recipe = Recipe.objects.create(household=self.household, name="Chili", instructions="Kochen.")
        ingredient = Ingredient.objects.create(name="Paprika")
        RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=1)
        url = reverse("recipes:recipe_detail", args=[recipe.pk])

        response = self.client.get(url)
        self.assertContains(response, 'id="pane-ingredients"')
        self.assertContains(response, 'id="pane-instructions"')
        self.assertNotContains(response, 'id="pane-deals"')

        self.deal("Paprika", "Lidl", "1.29")
        self.assertContains(self.client.get(url), 'id="pane-deals"')
