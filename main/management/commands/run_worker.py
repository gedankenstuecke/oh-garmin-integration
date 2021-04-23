import logging

from django.core.management.base import BaseCommand

_LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run threads that will process the async tasks'

    def handle(self, *args, **options):
        from dotenv import load_dotenv

        load_dotenv()

        from main.worker import start_worker_threads

        _LOGGER.info("Starting worker threads")
        start_worker_threads()
