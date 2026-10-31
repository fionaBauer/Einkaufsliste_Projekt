from django.core.management.base import BaseCommand

from recipes.images import optimize_recipe_image
from recipes.models import Recipe


class Command(BaseCommand):
    help = "Verkleinert vorhandene Rezeptbilder und erzeugt Vorschaubilder (idempotent)."

    def handle(self, *args, **options):
        done = skipped = 0
        for recipe in Recipe.objects.exclude(image="").exclude(image__isnull=True).iterator():
            if not recipe.image.storage.exists(recipe.image.name):
                skipped += 1
                continue
            new_name = optimize_recipe_image(recipe.image)
            if new_name is None:
                skipped += 1
                continue
            if new_name != recipe.image.name:
                Recipe.objects.filter(pk=recipe.pk).update(image=new_name)
            done += 1
        self.stdout.write(self.style.SUCCESS(f"{done} Bilder optimiert, {skipped} übersprungen."))
