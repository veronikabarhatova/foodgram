import base64

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from djoser.serializers import (UserCreateSerializer
                                as DjoserUserCreateSerializer,
                                UserSerializer
                                as DjoserUserSerializer)
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShortLink, ShoppingCart,
                            Tag)
from users.models import Follow, User


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        """Настраиваем изображение."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(DjoserUserCreateSerializer, DjoserUserSerializer):
    """Сериализатор для создания и обновления пользователя."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False)

    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=('Username должен содержать только буквы, цифры '
                         ' и следующие символы: @/./+/-/_'),
                code='invalid_username'
            ),
            UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'password', 'is_subscribed', 'avatar')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True, 'write_only': True},
            'avatar': {'required': False},
        }

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return obj.following.filter(user=user, author=obj).exists()

    def validate(self, attrs):
        if 'password' in attrs and 'user' in self.context:
            validate_password(attrs['password'], self.context['user'])
        return attrs

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('avatar_only'):
            return {'avatar': data['avatar']}
        registration = self.context.get('registration', False)
        if registration:
            data.pop('is_subscribed', None)
            data.pop('avatar', None)
        return data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('__all__')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""
    id = serializers.ReadOnlyField(
        source='ingredient.id')
    name = serializers.ReadOnlyField(
        source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецепта."""
    tags = TagSerializer(read_only=True, many=True)
    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipeingredient_set',
        read_only=True, many=True)
    is_favorited = serializers.BooleanField(
        read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text',
                  'cooking_time')

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы 1 ингредиент')
        ingredient_list = []
        for ingredient_item in ingredients:
            ingredient_instance = Ingredient.objects.filter(
                id=ingredient_item.get('id')).first()
            if not ingredient_instance:
                raise serializers.ValidationError(
                    ('Такого ингредиента не существует!')
                )
            if ingredient_instance in ingredient_list:
                raise serializers.ValidationError(
                    ('Такой ингредиент уже добавлен!')
                )
            ingredient_list.append(ingredient_instance)
            if int(ingredient_item['amount']) <= 0:
                raise serializers.ValidationError(
                    ('Убедитесь, что количество ингредиентов '
                     'больше 0')
                )
        data['ingredients'] = ingredients
        tags = self.initial_data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы 1 тег')
        tags_list = []
        for tag_item in tags:
            tag_instance = Tag.objects.filter(
                id=tag_item).first()
            if not tag_instance:
                raise serializers.ValidationError(
                    ('Такого тега не существует!')
                )
            if tag_instance.id in [tag.id for tag in tags_list]:
                raise serializers.ValidationError(
                    ('Такой тег уже добавлен!')
                )
            tags_list.append(tag_instance)
        return data

    def create_ingredients(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient.get('amount', 0),
            )
            for ingredient in ingredients
        ])

    def create(self, validated_data):
        image = validated_data.pop('image')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(image=image, **validated_data)
        tags_data = self.initial_data.get('tags')
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        tags_data = self.initial_data.get('tags')
        instance.tags.set(tags_data)
        instance.ingredients.clear()
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            self.create_ingredients(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        include_extra_fields = self.context.get('include_extra_fields', False)
        if include_extra_fields:
            user = self.context['request'].user
            if user.is_authenticated:
                representation['is_favorited'] = instance.is_favorited
                representation['is_in_shopping_cart'] = (
                    instance.is_in_shopping_cart)
        return representation


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для короткого рецепта."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    class Meta:
        model = FavoriteRecipe
        fields = (
            'user',
            'recipe',
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=FavoriteRecipe.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном!'
            )
        ]

    def to_representation(self, instance):
        return ShortRecipeSerializer(instance.recipe).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = (
            'user',
            'recipe',
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок!'
            )
        ]

    def to_representation(self, instance):
        return ShortRecipeSerializer(instance.recipe).data


class ShortLinkSerializer(serializers.ModelSerializer):
    """Сериализатор для коротких ссылок."""
    class Meta:
        model = ShortLink
        fields = ('__all__',)


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
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
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar',
                  'author')
        model = Follow

    def get_avatar(self, obj):
        if obj.author.avatar:
            return obj.author.avatar.url
        return None

    def get_is_subscribed(self, obj):
        return obj.user.following.filter(author=obj.author).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit:
            queryset = queryset[:int(limit)]
        return ShortRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def validate_id(self, value):
        user_exists = User.objects.filter(id=value).exists()
        if not user_exists:
            raise serializers.ValidationError(
                'Пользователя с указанным id не существует.')
        return value

    def validate(self, data):
        user = self.context.get('request').user
        author = data.get('author')
        if author == user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.')
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not request.user.is_staff:
            data.pop('author', None)
        return data
