# Проект «Foodgram»
## "Foodgram" - это онлайн-платформа, где пользователи могут делиться своими любимыми рецептами, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Основной функционал включает в себя также сервис "Список покупок", который помогает создавать список продуктов, необходимых для приготовления выбранных блюд.

### Стек технологий:

- Python 3.9
- Django 3.2.16
- Django REST framework 3.15
- Nginx
- Docker
- PostgreSQL

### Особенности проекта:

- **Публикация рецептов:** Пользователи могут публиковать свои рецепты с подробными инструкциями и фотографиями.
- **Избранное:** Возможность добавлять понравившиеся рецепты в список избранных для последующего доступа.
- **Подписки:** Пользователи могут подписываться на других авторов и смотреть их рецепты.
- **Список покупок:** Удобный сервис для создания и скачивания списка продуктов, необходимых для приготовления выбранных блюд.
- **Аватарки:** Возможность загрузки и смены аватарки пользователя для персонализации профиля.
- **Короткие ссылки:** Генерация коротких ссылок на рецепты для удобного обмена и распространения.

### Порядок установки API:

Клонировать репозиторий и перейти в него в командной строке:
```sh
git clone git@github.com:veronikabarhatova/foodgram.git
```

```sh
cd foodgram 
```

**Cоздать и активировать виртуальное окружение:**

```sh
python3 -m venv venv
```

```sh
source venv/bin/activate
```

**Установить зависимости из файла requirements.txt:**

```sh
python3 -m pip install --upgrade pip
```

```sh
cd backend 
```

```sh
pip install -r requirements.txt
```

**Выполнить миграции:**

```sh
python3 manage.py migrate
```

**Запустить проект:**

```sh
python3 manage.py runserver
```

### Запуск на сайте:

**Создать файл .env в корне проекта и записать данные для подлючения к базе данных и настроек settings.py**
```.env
POSTGRES_USER=django_user
POSTGRES_PASSWORD=password
POSTGRES_DB=django
DB_HOST=db
DB_PORT=5432
SECRET_KEY=****
DEBUG=True
ALLOWED_HOSTS=site1,site2,site3
```
**Запустить сборку проета**

```bash
sudo docker compose up
```

### Примеры запросов к API:

**Регистрация пользователя**

POST ```https://foodgram.line.pm/api/users/```

Данные запроса:
```json
{
    "email": "vpupkin@yandex.ru",
    "username": "vasya.pupkin",
    "first_name": "Вася",
    "last_name": "Иванов",
    "password": "Qwerty123"
}
```
Ответ:
```json
{
    "email": "vpupkin@yandex.ru",
    "id": 0,
    "username": "vasya.pupkin",
    "first_name": "Вася",
    "last_name": "Иванов"
}
```
**Добавление аватара**

Данные запроса:
```json
{
    "avatar": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg=="
}
```
Ответ:
```json
{
    "avatar": "http://foodgram.line.pm/media/users/image.png"
}
```

**Получение токена**

POST ```https://foodgram.line.pm/api/auth/tocken/login/```

Данные запроса:
```json
{
    "password": "string",
    "email": "string"
}
```
Ответ:
```json
{
    "auth_token": "string"
}
```

**Получение списка тегов**

GET ```https://foodgram.line.pm/api/tags/```

Ответ::
```json
[
  {
    "id": 0,
    "name": "Завтрак",
    "slug": "breakfast"
  }
]
```

**Получение списка рецептов**

GET ```https://foodgram.line.pm/api/recipes/```

Ответ:
```json
{
  "count": 123,
  "next": "http://foodgram.line.pm/api/recipes/?page=4",
  "previous": "http://foodgram.example.org/api/recipes/?page=2",
  "results": [
    {
      "id": 0,
      "tags": [
        {
          "id": 0,
          "name": "Завтрак",
          "color": "#E26C2D",
          "slug": "breakfast"
        }
      ],
      "author": {
        "email": "user@example.com",
        "id": 0,
        "username": "string",
        "first_name": "Вася",
        "last_name": "Пупкин",
        "is_subscribed": false
      },
      "ingredients": [
        {
          "id": 0,
          "name": "Картофель отварной",
          "measurement_unit": "г",
          "amount": 1
        }
      ],
      "is_favorited": true,
      "is_in_shopping_cart": true,
      "name": "string",
      "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
      "text": "string",
      "cooking_time": 1
    }
  ]
}
```

**Создание рецепта**

POST ```https://foodgram.line.pm/api/recipes/```

Данные запроса:
```json
{
  "ingredients": [
    {
      "id": 1123,
      "amount": 10
    }
  ],
  "tags": [
    1,
    2
  ],
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
  "name": "string",
  "text": "string",
  "cooking_time": 1
}
```
Ответ:
```json
{
  "id": 0,
  "tags": [
    {
      "id": 0,
      "name": "Завтрак",
      "color": "#E26C2D",
      "slug": "breakfast"
    }
  ],
  "author": {
    "email": "user@example.com",
    "id": 0,
    "username": "string",
    "first_name": "Вася",
    "last_name": "Иванов",
    "is_subscribed": false
  },
  "ingredients": [
    {
      "id": 0,
      "name": "Картофель отварной",
      "measurement_unit": "г",
      "amount": 1
    }
  ],
  "is_favorited": true,
  "is_in_shopping_cart": true,
  "name": "string",
  "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
  "text": "string",
  "cooking_time": 1
}
```
**Добавить/удалить рецепт в список покупок**

POST/DELETE ```https://foodgram.line.pm/api/recipes/{id}/shopping_cart/```

Ответ:
```json
{
    "id": 0,
    "name": "string",
    "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
    "cooking_time": 1
}
```

**Получить короткую ссылку на рецепт**

GET ```https://foodgram.line.pm/api/recipes/{id}/get-link/```

Ответ:
```json
{
    "short-link": "https://foodgram.example.org/s/3d0"
}
```

**Скачать список покупок**

GET ```https://foodgram.line.pm/api/recipes/download_shopping_cart/```

**Добавить/удалить рецепт в избранное**

POST/DELETE ```https://foodgram.line.pm/api/recipes/{id}/favorite/```

Ответ:
```json
{
    "id": 0,
    "name": "string",
    "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
    "cooking_time": 1
}
```
**Мои подписки**

GET ```https://foodgram.line.pm/api/users/subsciptions```

Ответ:
```json
{
  "count": 123,
  "next": "http://foodgram.line.pm/api/users/subscriptions/?page=4",
  "previous": "http://foodgram.line.pm/api/users/subscriptions/?page=2",
  "results": [
    {
      "email": "user@example.com",
      "id": 0,
      "username": "string",
      "first_name": "Вася",
      "last_name": "Иванов",
      "is_subscribed": true,
      "recipes": [
        {
          "id": 0,
          "name": "string",
          "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
          "cooking_time": 1
        }
      ],
      "recipes_count": 0
    }
  ]
}
```
**Подписаться на пользователя**

POST/DELETE ```https://foodgram.line.pm/api/recipes/{id}/subscribe/```

Ответ:
```json 
{
  "email": "user@example.com",
  "id": 0,
  "username": "string",
  "first_name": "Вася",
  "last_name": "Иванов",
  "is_subscribed": true,
  "recipes": [
    {
      "id": 0,
      "name": "string",
      "image": "http://foodgram.line.pm/media/recipes/images/image.jpeg",
      "cooking_time": 1
    }
  ],
  "recipes_count": 0
}
```
**Список ингредиентов**

GET ```https://foodgram.line.pm/api/ingredients/```

Ответ:
```json
[
  {
    "id": 0,
    "name": "Капуста",
    "measurement_unit": "кг"
  }
]
```

Ссылка на сайт: ```https://foodgram.line.pm/```  
Почта адина: ```cola@mail.ru```  
Пароль от админки: ```qwertyasd123```