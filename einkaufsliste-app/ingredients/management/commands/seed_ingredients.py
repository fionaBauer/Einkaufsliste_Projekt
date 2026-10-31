from django.core.management.base import BaseCommand

from ingredients.models import Ingredient
from ingredients.seed_data import iter_seed_ingredients


class Command(BaseCommand):
    help = "Spielt das eingebaute Lebensmittel-Wörterbuch ein (nur fehlende Einträge, idempotent)."

    def handle(self, *args, **options):
        existing = {name.lower() for name in Ingredient.objects.values_list("name", flat=True)}
        to_create = []
        for name, category, unit in iter_seed_ingredients():
            if name.lower() in existing:
                continue
            existing.add(name.lower())
            to_create.append(Ingredient(name=name, category=category, default_unit=unit))

        Ingredient.objects.bulk_create(to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"{len(to_create)} Zutaten ergänzt."))
