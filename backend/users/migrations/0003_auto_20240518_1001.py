# Generated by Django 3.2.16 on 2024-05-18 10:01

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20240516_1432'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='follow',
            name='unique_self_following',
        ),
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.UniqueConstraint(condition=models.Q(('user', django.db.models.expressions.F('author'))), fields=('user', 'author'), name='unique_self_following'),
        ),
    ]