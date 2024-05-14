from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from recipes.models import ShortLink


def redirection(request, short_url):
    try:
        shortlink = ShortLink.objects.get(short_url=short_url)
        return redirect(shortlink.full_url)
    except ShortLink.DoesNotExist:
        return HttpResponseNotFound(f'Страница не найдена - {short_url}')
