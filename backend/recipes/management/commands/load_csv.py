import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open(
            os.path.join(
                settings.BASE_DIR,
                'data', 'ingredients.csv'
            ),
            'r', encoding='utf-8'
        ) as f:
            csv_reader = csv.reader(f, delimiter=',')
            for name, measurement_unit in csv_reader:
                ingredient, created = Ingredient.objects.get_or_create(
                    name=name,
                    measurement_unit=measurement_unit)
                if not created:
                    self.stdout.write(self.style.WARNING(
                        f'Ингредиент "{name}" уже существует.'))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'Ингредиент "{name}" успешно создан.'))
