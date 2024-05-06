import django_filters
from django.contrib.auth import get_user_model

from recipes.models import Recipe

User = get_user_model()


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    tags = django_filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = django_filters.BooleanFilter(
        method='filter_by_is_favorited')
    is_in_shopping_cart = django_filters.BooleanFilter(
        method='filter_by_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['tags', 'author']

    def filter_by_is_favorited(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_by_is_in_shopping_cart(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(cart__user=self.request.user)
        return queryset
