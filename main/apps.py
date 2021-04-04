import logging
import os
import sys

from django.apps import AppConfig

_LOGGER = logging.getLogger(__name__)


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        import main.signals  # noqa

        if is_main_exec():
            from main.tasks import start_threads
            start_threads()
            _LOGGER.info("Started processing threads")


def is_main_exec():
    if os.environ.get('RUN_MAIN') == 'true':
        # Main process of debug server with restart on file changes (not the file watcher process)
        return True

    if '--noreload' in sys.argv:
        # Debug server without restart on file changes
        return True

    server_software_var = os.environ.get('SERVER_SOFTWARE')
    if server_software_var is not None and 'gunicorn' in server_software_var:
        # Ran by gunicorn
        return True
