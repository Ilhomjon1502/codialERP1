FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.prod
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Statik fayllar (Django admin, API hujjati) — build paytida yig'iladi; vaqtinchalik kalit faqat shu buyruq uchun
RUN SECRET_KEY=build-only-not-used-at-runtime-0123456789abcdef python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p /app/media && chown -R app /app
USER app
EXPOSE 8000

# Har ishga tushganda migratsiyalar qo'llanadi, keyin Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile -"]
