def show_wechat_login_code(origin_cls, url):
    print('\nScan the code with Wechat to log into `{}`:'.format(
        origin_cls.full_name))
    print(url)


DEFAULT_SETTINGS = {
    'MAX_PAGE_RETRY': 2,
    'TIMEOUT': 3,
    'REQUEST_MAX_RETRY': 1,
    'AUTO_LATEST': True,
    'CACHE_DIR': '.sscn_cache',
    'SHOW_WECHAT_LOGIN_CODE_FUNC': show_wechat_login_code,
    'MAX_SEARCH_PAGES': 20,
}


class Settings:
    def __init__(self, **kwargs):
        self.default_settings = DEFAULT_SETTINGS
        self.user_settings = kwargs

    def __getitem__(self, name):
        if name in self.user_settings:
            return self.user_settings[name]
        else:
            return self.default_settings[name]

    def __setitem__(self, name, value):
        self.user_settings[name] = value

    def __delitem__(self, name):
        self.user_settings.__delattr__(name)

    def get(self, name, default=None):
        try:
            val = self[name]
        except KeyError:
            return default
        else:
            return val

    def update(self, settings):
        self.user_settings.update(settings)


settings = Settings()
