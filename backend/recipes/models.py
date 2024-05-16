from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (MAX_LEN_ING, MAX_LEN_UNIT, MAX_LEN_TAG,
                        MAX_LEN_RECIPE, MIN_VALUE, MAX_COOKING_TIME)

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингридиента."""
    name = models.CharField(
        max_length=MAX_LEN_ING,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LEN_UNIT,
        verbose_name='Единица измерения'
    )

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}.'

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(fields=['name', 'measurement_unit'],
                                    name='unique_name_measurement_unit')
        ]


class Tag(models.Model):
    """Модель тэга."""
    name = models.CharField(
        max_length=MAX_LEN_TAG,
        unique=True,
        verbose_name='Название тега'
    )
    slug = models.SlugField(
        unique=True,
        max_length=MAX_LEN_TAG,
        verbose_name='Слаг'
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class Recipe(models.Model):
    """Модель рецепта."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор публикации'
    )
    name = models.CharField(
        max_length=MAX_LEN_RECIPE,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        blank=True,
        null=True,
        default=None
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        through='RecipeIngredient'
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name='Тэги'
    )
    cooking_time = models.PositiveSmallIntegerField(validators=(
        MinValueValidator(
            MIN_VALUE,
            message='Количество должно быть не меньше 1'
        ),
        MaxValueValidator(
            MAX_COOKING_TIME,
            message='Слишком большое значение времени приготовления'
        )),
        verbose_name='Время приготовления'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Модель ингридиентов в рецепте."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(validators=(
        MinValueValidator(
            MIN_VALUE,
            message='Количество должно быть не меньше 1'
        ),
        MaxValueValidator(
            MAX_COOKING_TIME,
            message='Слишком большое значение ингредиентов'
        )),
    )

    class Meta:
        ordering = ('ingredient',)
        constraints = (
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'), name='unique_ingredient'
            ),
        )
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class BaseUserRecipe(models.Model):
    """Абстрактная модель для списка покупок и избранного."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True


class FavoriteRecipe(BaseUserRecipe):
    """Модель избранных рецептов."""

    class Meta:
        default_related_name = 'favorites'
        ordering = ('recipe',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite'
            ),
        )
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user} добавил в избранное {self.recipe.name}'


class ShoppingCart(BaseUserRecipe):
    """Модель списка покупок."""

    class Meta:
        default_related_name = 'cart'
        ordering = ('recipe',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_cart'
            ),
        )
        verbose_name = 'Список покупок'
        verbose_name_plural = 'В списке покупок'

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name} в список'


class ShortLink(models.Model):
    """Модель короткой ссылки."""
    short_url = models.CharField(
        max_length=MAX_LEN_ING,
        unique=True,
        verbose_name='Короткая ссылка')
    full_url = models.CharField(
        max_length=MAX_LEN_ING,
        unique=True,
        verbose_name='Полная ссылка')
    recipe = models.OneToOneField(
        Recipe,
        on_delete=models.CASCADE,
        related_name='short_links')

    def __str__(self):
        return self.short_url
