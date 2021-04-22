import logging

from django.apps import AppConfig

_LOGGER = logging.getLogger(__name__)


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        import main.signals  # noqa
