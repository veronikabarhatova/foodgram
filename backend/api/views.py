import hashlib

from django.db.models import BooleanField, Case, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, ShortLink, Tag)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import OwnerOrReadOnly
from .serializers import (CommonRecipeSerializer, IngredientSerializer,
                          RecipeSerializer, TagSerializer)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    filter_backends = (DjangoFilterBackend, )
    search_fields = ('^name',)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет Тегов."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = CustomPagination
    permission_classes = (OwnerOrReadOnly, IsAuthenticatedOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = Recipe.objects.all()

        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None:
            is_favorited_bool = bool(int(is_favorited))
            if not self.request.user.is_anonymous:
                queryset = queryset.annotate(
                    is_favorited=Case(
                        When(favorites__user=self.request.user, then=True),
                        default=False,
                        output_field=BooleanField()
                    )
                ).filter(is_favorited=is_favorited_bool)

        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        if is_in_shopping_cart is not None:
            is_in_shopping_cart_bool = bool(int(is_in_shopping_cart))
            if not self.request.user.is_anonymous:
                queryset = queryset.annotate(
                    is_in_shopping_cart=Case(
                        When(cart__user=self.request.user, then=True),
                        default=False,
                        output_field=BooleanField()
                    )
                ).filter(is_in_shopping_cart=is_in_shopping_cart_bool)

        return queryset

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецета в избранное."""
        user = request.user
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=pk)
            except Recipe.DoesNotExist:
                raise ValidationError(
                    'Рецепт с указанным ID не существует.')
            if FavoriteRecipe.objects.filter(
                    user=user, recipe__id=pk).exists():
                return Response({
                    'error': 'Рецепт уже добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST)
            recipe = get_object_or_404(Recipe, id=pk)
            FavoriteRecipe.objects.create(
                user=user, recipe=recipe
            )
            serializer = CommonRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            try:
                recipe_exist = get_object_or_404(Recipe, id=pk)
                recipe = FavoriteRecipe.objects.get(
                    user=user, recipe__id=recipe_exist.id)
            except FavoriteRecipe.DoesNotExist:
                raise ValidationError('Рецепт не был добавлен в избранное')
            recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в корзину."""
        user = request.user
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=pk)
            except Recipe.DoesNotExist:
                raise ValidationError(
                    'Рецепт с указанным ID не существует.')
            if ShoppingCart.objects.filter(
                    user=user, recipe__id=pk).exists():
                return Response({
                    'error': 'Рецепт уже добавлен в список'},
                    status=status.HTTP_400_BAD_REQUEST)
            recipe = get_object_or_404(Recipe, id=pk)
            ShoppingCart.objects.create(
                user=user, recipe=recipe)
            serializer = CommonRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            try:
                recipe_exist = get_object_or_404(Recipe, id=pk)
                cart_item = ShoppingCart.objects.get(
                    user=user,
                    recipe__id=recipe_exist.id)
            except ShoppingCart.DoesNotExist:
                raise ValidationError('Рецепт не был добавлен в корзину')
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок."""
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        ingredients_dict = {}
        for item in shopping_cart_items:
            recipe = item.recipe
            recipe_ingredients = RecipeIngredient.objects.filter(
                recipe=recipe
            )
            for recipe_ingredient in recipe_ingredients:
                ingredient_name = recipe_ingredient.ingredient.name
                ingredient_unit = recipe_ingredient.ingredient.measurement_unit
                ingredient_amount = recipe_ingredient.amount
                if ingredient_name in ingredients_dict:
                    ingredients_dict[ingredient_name][0] += ingredient_amount
                else:
                    ingredients_dict[ingredient_name] = [
                        ingredient_amount, ingredient_unit]
        ingredients_list = []
        for ingr_name, (ingr_amount, ingr_unit) in ingredients_dict.items():
            ingredient_str = f'{ingr_name} ({ingr_amount} {ingr_unit})'
            ingredients_list.append(ingredient_str)
        shopping_list_text = '\n'.join(ingredients_list)

        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_list.txt"')
        response.write(shopping_list_text)

        return response

    @action(detail=True, methods=['get'], url_path='get-link',
            permission_classes=[AllowAny])
    def get_link(self, request, *args, **kwargs):
        recipe = self.get_object()
        host = request.get_host()
        base_url = f'http://{host}/'
        full_url = f'{base_url}recipes/{recipe.id}'
        short_link = self.generate_short_link_for_recipe(recipe)
        short_url = f'{base_url}{short_link}/'
        existing_short_link = ShortLink.objects.filter(
            full_url=full_url, short_url=short_link, recipe=recipe).first()
        if existing_short_link:
            return JsonResponse({'short-link': short_url})
        else:
            ShortLink.objects.create(full_url=full_url, short_url=short_link,
                                     recipe=recipe)
            return JsonResponse({'short-link': short_url})

    def generate_short_link_for_recipe(self, recipe):
        recipe_id_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:10]
        return f'{recipe_id_hash}'
