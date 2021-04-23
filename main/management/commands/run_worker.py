from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run threads that will process the async tasks'

    def handle(self, *args, **options):
        from dotenv import load_dotenv

        load_dotenv()

        from main.worker import start_worker_threads

        start_worker_threads()
