import hashlib

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, ShortLink, Tag)
from users.models import Follow
from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import OwnerOrReadOnly
from .serializers import (FavoriteSerializer, FollowSerializer,
                          IngredientSerializer, RecipeSerializer,
                          ShoppingCartSerializer, ShortRecipeSerializer,
                          TagSerializer, UserSerializer)
from .services import annotate_recipes_with_user_flags


User = get_user_model()


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['include_extra_fields'] = (self.action == 'retrieve'
                                           or self.action == 'list')
        return context

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        annotated_queryset = annotate_recipes_with_user_flags(
            Recipe.objects.filter(pk=recipe.pk), self.request.user)
        annotated_recipe = annotated_queryset.first()
        serializer.instance.is_favorited = annotated_recipe.is_favorited
        serializer.instance.is_in_shopping_cart = (
            annotated_recipe.is_in_shopping_cart)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        context = self.get_serializer_context()
        context['include_extra_fields'] = True
        serializer = self.get_serializer(serializer.instance, context=context)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def get_queryset(self):
        queryset = Recipe.objects.all()
        user = self.request.user

        queryset = annotate_recipes_with_user_flags(queryset, user)

        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None:
            is_favorited_bool = bool(int(is_favorited))
            queryset = queryset.filter(
                is_favorited=is_favorited_bool)

        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        if is_in_shopping_cart is not None:
            is_in_shopping_cart_bool = bool(int(is_in_shopping_cart))
            queryset = queryset.filter(
                is_in_shopping_cart=is_in_shopping_cart_bool)

        return queryset.distinct()

    def get_object(self):
        queryset = self.get_queryset()
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_field]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    @staticmethod
    def add_to_cart_or_favorites(request, pk, serializer_class):
        """Статичный метод для добавления в корзину/избранное."""
        user = request.user
        # recipe = Recipe.objects.get(pk=pk)
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = serializer_class(data={'user': user.id,
                                            'recipe': recipe.id})
        if serializer.is_valid():
            serializer.save()
            short_recipe_serializer = ShortRecipeSerializer(recipe)
            return Response(
                short_recipe_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def remove_from_cart_or_favorites(request, pk, model_class):
        """Статичный метод для удаления из корзины/избранного."""
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        try:
            instance = model_class.objects.get(user=user, recipe=recipe)
        except model_class.DoesNotExist:
            raise exceptions.ValidationError(
                'Рецепт не был добавлен в избранное')

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление рецепта в избранное."""
        return self.add_to_cart_or_favorites(
            request, pk, FavoriteSerializer)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удаление рецепта из избранного."""
        return self.remove_from_cart_or_favorites(request, pk, FavoriteRecipe)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление рецепта в корзину."""
        return self.add_to_cart_or_favorites(
            request, pk, ShoppingCartSerializer)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удаление рецепта из корзины."""
        return self.remove_from_cart_or_favorites(request, pk, ShoppingCart)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка продуктов."""
        ingredients_agg = RecipeIngredient.objects.filter(
            recipe__cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        )
        ingredients_list = [
            f"{ingredient['ingredient__name']} "
            f"({ingredient['total_amount']} "
            f"{ingredient['ingredient__measurement_unit']})"
            for ingredient in ingredients_agg
        ]
        shopping_list_text = '\n'.join(ingredients_list)
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        response.write(shopping_list_text)
        return response

    @action(detail=True, methods=['get'], url_path='get-link',
            permission_classes=[AllowAny])
    def get_link(self, request, *args, **kwargs):
        """Получение короткой ссылки на рецепт."""
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
        ShortLink.objects.create(full_url=full_url, short_url=short_link,
                                 recipe=recipe)
        return JsonResponse({'short-link': short_url})

    def generate_short_link_for_recipe(self, recipe):
        recipe_id_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:10]
        return f'{recipe_id_hash}'


class UserViewSet(DjoserUserViewSet):
    """Вьюсет для пользователя."""
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action in ["list", "create", "retrieve"]:
            return [AllowAny()]
        elif self.action == 'me':
            return [IsAuthenticated()]
        else:
            return super().get_permissions()

    @action(methods=['get'], detail=False,
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Подписки пользователя."""
        queryset = Follow.objects.filter(user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        """Подписаться/отписаться от пользователя."""
        author = get_object_or_404(User, pk=id)
        serializer = FollowSerializer(data={'user': request.user.id,
                                            'author': author.id},
                                      context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, author=author)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        try:
            follow = Follow.objects.get(user=request.user, author=author)
        except Follow.DoesNotExist:
            return Response({'error': 'Подписка не существует'},
                            status=status.HTTP_400_BAD_REQUEST)

        follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put', 'patch', 'delete'], detail=False,
            url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def put_avatar(self, request):
        """Установка аватара пользователя."""
        user = request.user
        if request.method in ['PUT', 'PATCH']:
            avatar_data = request.data.get('avatar')
            if avatar_data is None:
                return Response(
                    {'error': 'Данные аватара не были предоставлены'},
                    status=status.HTTP_400_BAD_REQUEST)
            serializer = UserSerializer(
                instance=user, data={'avatar': avatar_data},
                partial=True,
                context={'request': request,
                         'avatar_only': True}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response({'message': 'Аватар успешно удален'},
                            status=status.HTTP_204_NO_CONTENT)
