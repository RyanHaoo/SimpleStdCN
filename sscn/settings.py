def show_wechat_login_code(origin_cls, url):
    """Display wechat login code in terminal."""
    print(f'\nScan the code with Wechat to log into `{origin_cls.full_name}`:')
    print(url)


DEFAULT_SETTINGS = {
    'MAX_PAGE_RETRY': 2,
    'TIMEOUT': 3,
    'REQUEST_MAX_RETRY': 1,
    'AUTO_LATEST': True,
    'CACHE_DIR': '.sscn_cache',
    'SHOW_WECHAT_LOGIN_CODE_FUNC': show_wechat_login_code,
    'MAX_SEARCH_PAGES': 16,
}


class Settings:
    """Class for application settings."""
    def __init__(self, **kwargs):
        self.default_settings = DEFAULT_SETTINGS
        self.user_settings = kwargs

    def __getitem__(self, name):
        if name in self.user_settings:
            return self.user_settings[name]
        return self.default_settings[name]

    def __setitem__(self, name, value):
        self.user_settings[name] = value

    def __delitem__(self, name):
        self.user_settings.__delattr__(name)

    def get(self, name, default=None):
        """Get a setting by `name`.
        
        `default` is returned if setting `name` isn't found.
        """
        try:
            val = self[name]
        except KeyError:
            return default
        return val

    def update(self, new_settings):
        """Upadate settings with a dict `new_settings`"""
        self.user_settings.update(new_settings)


settings = Settings()
