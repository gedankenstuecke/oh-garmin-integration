release: python manage.py migrate
web: gunicorn --reload oh_template.wsgi --log-file=-
worker: python manage.py run_tasks