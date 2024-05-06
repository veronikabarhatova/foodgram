from django.contrib import admin
from django.contrib.admin import display

from .models import FavoriteRecipe, Ingredient, Recipe, ShoppingCart, Tag


class IngridientsInline(admin.TabularInline):
    model = Recipe.ingredients.through


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'count_favorites', 'get_ingredients')
    list_filter = ('author', 'name', 'tags')
    search_fields = ('name', 'author__username', 'tags__name')
    readonly_fields = ('count_favorites',)
    inlines = [IngridientsInline]
    exclude = ('ingredients',)

    @display(description='Количество в избранном')
    def count_favorites(self, obj):
        return obj.favorites.count()

    def get_ingredients(self, obj):
        return ", ".join(ing.name for ing in obj.ingredients.all())

    get_ingredients.short_description = 'Ингредиенты'


admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart)
admin.site.register(FavoriteRecipe)
