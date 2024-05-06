from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from .constants import Constants

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингридиента."""
    name = models.CharField(
        max_length=Constants.MAX_LEN_ING,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=Constants.MAX_LEN_UNIT,
        verbose_name='Единица измерения'
    )

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}.'

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Tag(models.Model):
    """Модель тэга."""
    name = models.CharField(
        max_length=Constants.MAX_LEN_TAG,
        unique=True,
        verbose_name='Название тега'
    )
    slug = models.SlugField(
        unique=True,
        max_length=Constants.MAX_LEN_TAG,
        verbose_name='Слаг'
    )

    def __str__(self):
        return self.name

    class Meta:
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
        max_length=Constants.MAX_LEN_RECIPE,
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
    cooking_time = models.PositiveIntegerField(validators=(
        MinValueValidator(
            Constants.MIN_VALUE,
            message='Количество должно быть не меньше 1'
        ),),
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
        ordering = ('-pub_date',)

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
    amount = models.PositiveIntegerField(validators=(
        MinValueValidator(
            Constants.MIN_VALUE,
            message='Количество должно быть не меньше 1'
        ),
    ))

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


class FavoriteRecipe(models.Model):
    """Модель избранных рецептов."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta:
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


class ShoppingCart(models.Model):
    """Модель списка покупок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Рецепт'
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Список покупок'
        verbose_name_plural = 'В списке покупок'

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name} в список'
