from django.shortcuts import get_object_or_404
import shortuuid
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.http import JsonResponse

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from recipes.models import (FavoriteRecipe, Ingredient, RecipeIngredient,
                            Recipe, ShoppingCart, Tag)
from .serializers import (CommonRecipeSerializer, IngredientSerializer,
                          RecipeSerializer, TagSerializer)
from .filters import RecipeFilter
from .pagination import CustomPagination
from .permissions import OwnerOrReadOnly, AdminOrReadOnly


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AdminOrReadOnly,)
    filter_backends = (filters.SearchFilter, )
    search_fields = ('^name',)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет Тегов."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AdminOrReadOnly,)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = CustomPagination
    permission_classes = (OwnerOrReadOnly, )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    # # def get_queryset(self, request):
    # #     queryset = Recipe.objects.all()
    # #     page = self.paginate_queryset(queryset)
    # #     if page is not None:
    # #         serializer = RecipeSerializer(
    # #             page, many=True, context={'request': request}
    # #         )
    # #         return self.get_paginated_response(serializer.data)
    # #     serializer = RecipeSerializer(
    # #         queryset, many=True, context={'request': request}
    # #     )
    # #     return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецета в избранное."""
        user = request.user
        if request.method == 'POST':
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
        recipe = FavoriteRecipe.objects.filter(
            user=user, recipe__id=pk)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в корзину."""
        user = request.user
        if request.method == 'POST':
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
        recipe = ShoppingCart.objects.filter(user=user, recipe__id=pk)
        recipe.delete()
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
        short_link = self.generate_short_link_for_recipe(recipe)
        return JsonResponse({'short_link': short_link})

    def generate_short_link_for_recipe(self, recipe):
        current_host = self.request.get_host()
        short_id = shortuuid.uuid()[:3]
        base_url = f'https://{current_host}/recipes/'
        short_link = f'{base_url}{recipe.id}-{short_id}/'
        return short_link
