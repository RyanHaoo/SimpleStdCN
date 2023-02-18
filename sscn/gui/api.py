import os
import logging
from collections import OrderedDict

import yaml

from sscn.settings import settings
from sscn.utils import NotFound, get_absolute_path
from sscn.standard import Standard, StandardCode
from .folder import load_folder_tree, load_folder_file, load_downloaded_tree


logger = logging.getLogger(__name__)


class Api:
    def __init__(self):
        self.cached_standards = OrderedDict()
        self.window = None

    def _get_standard(self, code_str):
        code = StandardCode.parse(code_str)
        if code in self.cached_standards:
            return self.cached_standards[code]

        if len(self.cached_standards) >= settings['MAX_CACHED_STANDARDS']:
            self.cached_standards.popitem(last=False)

        std = Standard(code)
        self.cached_standards[code] = std
        return std

    def get_fields(self, code, fields):
        std = self._get_standard(code)
        results = {}
        for field in fields:
            value = std.get_field(field)
            if not isinstance(value, (str, list, dict)):
                value = str(value)
            results[field] = value

        logger.debug('Fields returned: {}'.format(results))
        return results

    def download_standard(self, code):
        std = self._get_standard(code)
        prefix = std.code.prefix
        
        # avoid using `parent=True` to avoid making a mess
        download_dir = get_absolute_path(settings['DOWNLOAD_DIR'])
        for dir_path in (download_dir, download_dir/prefix):
            if not dir_path.is_dir():
                dir_path.mkdir()

        file_path = dir_path / std.as_file_name()
        if file_path.exists():
            logger.info('file exists.')
            return 'EXISTS'

        content = std.get_field('pdf')
        if content is NotFound:
            logger.info('file not found.')
            return 'NOT_FOUND'
            
        with open(file_path, 'wb') as f:
            f.write(content)
        return True

    def open_standard_pdf(self, code):
        code = StandardCode.parse(code)
        dir_path = get_absolute_path(
            settings['DOWNLOAD_DIR']) / code.prefix
        assert dir_path.is_dir()

        matchings = list(dir_path.glob(f'{code.prefix}*{code.number}*{code.year}*.pdf'))
        if not matchings:
            return False
        assert len(matchings) == 1
        os.startfile(matchings[0])
        return True

    def save_settings(self):
        with open(self.settings_path, 'w', encoding='UTF8'
                ) as settings_file:
            yaml.safe_dump(settings.user_settings, settings_file)

    def load_folder_file(self, paths):
        file_path = get_absolute_path(settings['FOLDER_DIR']
            ).joinpath(*paths)
        if not file_path.is_file():
            return False
        
        return load_folder_file(file_path)

    def load_folder(self):
        folder_dir = get_absolute_path(settings['FOLDER_DIR'])
        tree = load_folder_tree(folder_dir)
        return tree

    def load_local(self):
        local_dir = get_absolute_path(settings['DOWNLOAD_DIR'])
        tree = load_downloaded_tree(local_dir)
        return tree

    def show_wechat_login_code(self, origin_cls, url):
        # TODO
        self.window.evaluate_js('showBZOrgLoginMessage("{}")'.format(url))

    def cancel_login(self, name):
        # TODO
        from sscn.origins import bzorg
        return bzorg.BZOrgOrigin.cancel_login()

    def close(self):
        self.window.destroy()

    def minimize(self):
        self.window.minimize()
