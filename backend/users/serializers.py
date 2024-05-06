from rest_framework import serializers
from djoser.serializers import UserSerializer, UserCreateSerializer
from rest_framework.validators import UniqueValidator
import base64
from django.core.files.base import ContentFile

from .models import Follow, User
from recipes.models import Recipe


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        """Настраиваем изображение."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CommonRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок и избранного."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(
        source='author.id')
    email = serializers.ReadOnlyField(
        source='author.email')
    username = serializers.ReadOnlyField(
        source='author.username')
    first_name = serializers.ReadOnlyField(
        source='author.first_name')
    last_name = serializers.ReadOnlyField(
        source='author.last_name')
    avatar = serializers.ReadOnlyField(
        source='author.avatar')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        fields = ('email', 'id', 'username', 'first_name', 'last_name'
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')
        model = Follow
        # validators = [
        #     validators.UniqueTogetherValidator(
        #         queryset=Follow.objects.all(),
        #         fields=('user', 'following')
        #     )
        # ]

    # def validate(self, data):
    #     if self.context.get('request').user == data.get('following'):
    #         raise serializers.ValidationError(
    #             'Нельзя подписаться на самого себя.')
    #     return data
    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit:
            queryset = queryset[:int(limit)]
        return CommonRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ['email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'avatar']

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj.id).exists()

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(
        max_length=150,
        validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ['email', 'id', 'username', 'first_name', 'last_name',
                  'password']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True},
        }
