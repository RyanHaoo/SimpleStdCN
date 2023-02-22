import os
import sys
import logging
from pathlib import Path

import yaml
import webview

from sscn.settings import settings
from sscn.gui.api import Api
from sscn.utils import get_absolute_path


os.environ['PATH'] += os.pathsep + str(Path(__file__).parent/'lib')
api = Api()

DEFAULT_SETTINGS = {
    'FOLDER_DIR': 'folders',
    'DOWNLOAD_DIR': 'download',
    'MAX_CACHED_STANDARDS': 5,
    'WEBVIEW_DEBUG': 0,
    'LOGGING_FORMAT': '%(asctime)s %(thread)d [%(levelname)s]: %(message)s',
    'LOGGING_DATEFMT': '%m/%d %H:%M:%S',
    'LOGGING_LEVEL': 'WARN',
    'LOGGING_FILE': 'sscn.log',
    'SHOW_WECHAT_LOGIN_CODE_FUNC': api.show_wechat_login_code
}
SETTINGS_FILE = 'config.yaml'
settings.default_settings.update(DEFAULT_SETTINGS)
logger = logging.getLogger(__name__)


def load_settings():
    """Load stored local setting."""
    path = get_absolute_path(SETTINGS_FILE)
    if not path.is_file():
        return None
    with open(path, encoding='UTF8') as settings_file:
        local_settings = yaml.safe_load(settings_file)
    settings.update(local_settings)
    return None


if __name__ == '__main__':
    load_settings()

    file_handler = logging.FileHandler(
        get_absolute_path(settings['LOGGING_FILE']),
        encoding='UTF8',
        mode='w',
    )
    handlers = [file_handler,]
    # StreamHandler causes error when frozen without a console
    if not getattr(sys, 'frozen', False):
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=settings['LOGGING_LEVEL'],
        format=settings['LOGGING_FORMAT'],
        datefmt=settings['LOGGING_DATEFMT'],
        handlers=handlers,
    )
    logger.debug('PATH: %s', os.environ['PATH'])

    window = webview.create_window(
        'SimpleStandardCN',
        './assets/layout.html',
        js_api=api,
        width=900,
        height=500,
        resizable=False,
        frameless=True,
        easy_drag=True,
        )
    api.window = window

    webview.start(debug=bool(settings['WEBVIEW_DEBUG']))
