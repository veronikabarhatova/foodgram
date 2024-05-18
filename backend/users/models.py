from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .constants import MAX_LEN_PASS_USER, MAX_LEN_USER, MAX_USER_EMAIL


class User(AbstractUser):
    """Модель пользователя."""
    username = models.CharField(
        unique=True,
        max_length=MAX_LEN_USER,
        verbose_name='Username',
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=('Username должен содержать только буквы, цифры '
                         ' и следующие символы: @/./+/-/_'),
                code='invalid_username'
            )
        ],
    )
    email = models.CharField(
        max_length=MAX_USER_EMAIL,
        verbose_name='Email'
    )
    last_name = models.CharField(
        max_length=MAX_LEN_USER,
        verbose_name='Фамилия'
    )
    first_name = models.CharField(
        max_length=MAX_LEN_USER,
        verbose_name='Имя'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )
    password = models.CharField(
        max_length=MAX_LEN_PASS_USER,
        verbose_name='Пароль'
    )

    class Meta:
        ordering = ['username']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Модель подписки."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        unique_together = ('user', 'author')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                condition=models.Q(user=models.F('author')),
                name='unique_self_following'
            )
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
