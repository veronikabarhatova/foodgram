from api.pagination import CustomPagination
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Follow
from .serializers import CustomUserSerializer, FollowSerializer

User = get_user_model()


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
        if page is not None:
            serializer = FollowSerializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = FollowSerializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        """Подписаться/отписаться от пользователя."""
        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if Follow.objects.filter(
                    author=author).exists():
                return Response({
                    'error': 'Вы уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST)
            follow = Follow.objects.create(
                user=request.user, author=author
            )
            serializer = FollowSerializer(
                follow, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            try:
                follow = Follow.objects.get(user=request.user, author=author)
            except Follow.DoesNotExist:
                raise ValidationError('Подписка не существует')
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put', 'patch', 'delete'], detail=False,
            url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def put_avatar(self, request):
        user = request.user
        avatar_data = request.data.get('avatar')
        if request.method in ['PUT', 'PATCH']:
            serializer = CustomUserSerializer(
                instance=user, data={'avatar': avatar_data},
                partial=True,
                context={'request': request,
                         'avatar_only': True}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_200_OK)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response({'message': 'Аватар успешно удален'},
                            status=status.HTTP_204_NO_CONTENT)
