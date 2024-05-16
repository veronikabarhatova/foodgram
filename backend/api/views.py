import hashlib

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import BooleanField, Case, Sum, When
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
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
from .serializers import (CommonRecipeSerializer, IngredientSerializer,
                          RecipeSerializer, TagSerializer,
                          CustomUserSerializer, FollowSerializer)


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

    @staticmethod
    def add_to_cart_or_favorites(request, pk,
                                 model_class, serializer_class):
        """Статичный метод для добавления в корзину/избранное."""
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не существует.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if model_class.objects.filter(user=user, recipe=recipe).exists():
            return Response({'detail': 'Этот элемент уже добавлен.'},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            model_class.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def remove_from_cart_or_favorites(request, pk, model_class):
        """Статичный метод для удаления из корзины/избранного."""
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            raise Http404('Рецепт не существует')
        try:
            instance = model_class.objects.get(user=user, recipe=recipe)
        except model_class.DoesNotExist:
            raise exceptions.ValidationError(
                'Рецепт не был добавлен в избранное')

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление рецепта в избранное."""
        if request.method == 'POST':
            return self.add_to_cart_or_favorites(
                request, pk, FavoriteRecipe, CommonRecipeSerializer)
        elif request.method == 'DELETE':
            return self.remove_from_cart_or_favorites(
                request, pk, FavoriteRecipe)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление рецепта в корзину."""
        if request.method == 'POST':
            return self.add_to_cart_or_favorites(
                request, pk, ShoppingCart, CommonRecipeSerializer)
        elif request.method == 'DELETE':
            return self.remove_from_cart_or_favorites(
                request, pk, ShoppingCart)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка продуктов."""
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        ingredients_agg = RecipeIngredient.objects.filter(
            recipe__in=shopping_cart_items.values('recipe')
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
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
        else:
            ShortLink.objects.create(full_url=full_url, short_url=short_link,
                                     recipe=recipe)
            return JsonResponse({'short-link': short_url})

    def generate_short_link_for_recipe(self, recipe):
        recipe_id_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:10]
        return f'{recipe_id_hash}'


class CustomUserViewSet(UserViewSet):
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

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        """Подписаться/отписаться от пользователя."""
        if request.method == 'POST':
            author = get_object_or_404(User, pk=id)
            serializer = FollowSerializer(data={'user': request.user.id,
                                                'author': author.id},
                                          context={'request': request})
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save(user=request.user, author=author)
                    return Response(serializer.data,
                                    status=status.HTTP_201_CREATED)
                except ValidationError as e:
                    return Response({'detail': str(e)},
                                    status=status.HTTP_400_BAD_REQUEST)
                except IntegrityError:
                    return Response(
                        {'detail': 'Вы уже подписаны на этого пользователя.'},
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
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
        avatar_data = request.data.get('avatar')
        if request.method in ['PUT', 'PATCH']:
            serializer = CustomUserSerializer(
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
