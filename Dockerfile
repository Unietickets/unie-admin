# Базовый Python-образ
FROM python:3.11-slim

# Переменные окружения для Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Рабочая директория
WORKDIR /unie-admin

# Копируем файлы проекта
COPY . /unie-admin/

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Создаём .env, если его нет
RUN [ -f .env ] || echo -e "FLASK_ENV=production\nMYSQL_HOST=localhost\nMYSQL_USER=postgres\nMYSQL_PASSWORD=admin\nMYSQL_DB=postgres\nMYSQL_PORT=5432" > .env

# Открываем порт
EXPOSE 5000

# Устанавливаем gunicorn для продакшена (если надо)
RUN pip install gunicorn

# Запуск приложения через gunicorn
# app:app — это путь до твоего Flask-приложения, проверь имя!
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
