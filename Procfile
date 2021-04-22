release: python manage.py migrate
web: gunicorn --reload oh_template.wsgi --log-file=-
tasks: python manage.py run_tasks