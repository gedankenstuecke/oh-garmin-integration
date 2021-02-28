release: python manage.py migrate
web: gunicorn --reload oh_template.wsgi --log-file=-
worker: celery -A oh_template worker --concurrency 1
