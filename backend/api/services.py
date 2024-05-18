from django.db.models import BooleanField, Value, Exists, OuterRef
from django.http import HttpResponseNotFound
from django.shortcuts import redirect

from recipes.models import FavoriteRecipe, ShortLink, ShoppingCart


def redirection(request, short_url):
    try:
        shortlink = ShortLink.objects.get(short_url=short_url)
        return redirect(shortlink.full_url)
    except ShortLink.DoesNotExist:
        return HttpResponseNotFound(f'Страница не найдена - {short_url}')


def annotate_recipes_with_user_flags(queryset, user):
    if user.is_authenticated:
        queryset = queryset.annotate(
            is_favorited=Exists(
                FavoriteRecipe.objects.filter(
                    user=user, recipe=OuterRef('pk')
                )
            ),
            is_in_shopping_cart=Exists(
                ShoppingCart.objects.filter(
                    user=user, recipe=OuterRef('pk')
                )
            )
        )
    else:
        queryset = queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField())
        )
    return queryset
