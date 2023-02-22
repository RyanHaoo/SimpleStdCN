import re
import os
import time
import logging
from urllib.parse import urljoin

import parsel

from ..settings import settings
from ..utils import NotFound, get_absolute_path
from ..exceptions import ContentUnavailable
from ..standard import Origin, StandardCode, Status
from ..page import DetailXPathPage, SearchXPathPage, PDFDownloader

# pylint: disable=missing-class-docstring
# no need

logger = logging.getLogger(__name__)


class BZOrgSearchPage(SearchXPathPage):
    public_fields = (
        'title', 'ics', 'ccs', 'issuance_date', 'implementation_date',
        'status',)
    origin_only_fields = ('detail_page_url',)

    search_url = r'https://www.biaozhun.org/plus/search.php'
    entry_xpath = r'//div[@class="list"]/ul/li'
    field_xpaths = {
        'detail_page_url': (r'./div[2]/div[1]/a/@href', NotFound),
        'ics': (r'./div[2]//span[@class="ccsicon"]/em/text()', NotFound),
        'ccs': (r'./div[2]//span[@class="icsicon"]/em/text()', NotFound),
        'issuance_date': (r'./div[3]//em[2]/text()', NotFound),
        'implementation_date': (r'./div[3]//em[1]/text()', NotFound),
        '_status': (r'.//div[@class="state"]/text()', NotFound),
    }
    _full_title_xpath = r'./div[2]/div[1]/a//text()'

    def get_query_params(self):
        code = self.origin.std.code
        search_str = f'{code.number}{f".{code.part}" if code.part else ""}-{code.year}'
        return {'q': search_str}

    def request(self, *args, **kwargs):
        query = self.get_query_params()
        kwargs['data'] = query
        return super().request(*args, method='POST', **kwargs)

    def is_entry_matching(self, entry):
        full_title = ''.join(
            entry.xpath(self._full_title_xpath).getall()
            )
        parsed = StandardCode.parse(full_title)
        return parsed == self.origin.std.code

    def extract_fields(self, content):
        fields = super().extract_fields(content)

        full_title = ''.join(
            content.xpath(self._full_title_xpath).getall()
            )
        fields['title'] = re.search(
            r'\d\s(.+)\s*$', full_title).groups()[0]

        fields['status'] = {
                '现行': Status.VALID,
                '即将实施': Status.ISSUED,
                '有更新版': Status.OBSOLETE,
                '已废止': Status.ABOLISHED,
                '已作废': Status.OBSOLETE,
            }[fields['_status']]
        return fields


class BZOrgDetailPage(DetailXPathPage):
    origin_only_fields = ('download_page_url',)

    url_field = 'detail_page_url'
    base_node_xpath = r'//div[@class="main"]'
    field_xpaths = {
        'download_page_url': (
            r'.//a[span]/@href', NotFound),
    }


class BZOrgDownloadPage(DetailXPathPage):
    origin_only_fields = ('download_1_url', 'download_2_url')

    url_field = 'download_page_url'
    base_node_xpath = r'//div[@class="download"]'
    field_xpaths = {
        'download_1_url': (r'./dt[1]/a/@href', NotFound),
        'download_2_url': (r'./dt[2]/a/@href', NotFound),
        }


class BZorgDownloader(PDFDownloader):
    pass


class BZorgDownloaderA(BZorgDownloader):
    url_field = 'download_1_url'


class BZorgDownloaderB(BZorgDownloader):
    url_field = 'download_2_url'


class BZOrgOrigin(Origin):
    """Source of standard: www.biaozhun.org (标准网)"""
    index = 'www.biaozhun.org'
    name = 'biaozhun'
    full_name = '标准网'
    pages = (
        BZOrgSearchPage, BZOrgDetailPage, BZOrgDownloadPage,
        BZorgDownloaderA, BZorgDownloaderB,)
    request_timeout = 6

    logged_in = False
    _cancel_login = False

    @classmethod
    def load_cached_session(cls):
        """Load cached session info from local file"""
        cache_path = get_absolute_path(settings['CACHE_DIR']) / cls.name
        if not cache_path.is_file():
            return False
        with cache_path.open(encoding='UTF-8') as file:
            for line in file.readlines():
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                cls.session.cookies.set(key.strip(), value.strip())
        return True

    @classmethod
    def cache_session(cls):
        """Cache session info to local file"""
        cache_dir = get_absolute_path(settings['CACHE_DIR'])
        if not cache_dir.is_dir():
            os.mkdir(cache_dir)

        cache_path =  cache_dir / cls.name
        with cache_path.open('w', encoding='UTF-8') as file:
            for key in (
                'DedeLoginTime', 'DedeLoginTime__ckMd5',
                'DedeUserID', 'DedeUserID__ckMd5',
                ):
                value = cls.session.cookies.get(key, '')
                file.write(f'{key}={value}\n')

    @classmethod
    def cancel_login(cls):
        """Cancel ongoing login process"""
        cls._cancel_login = True

    @classmethod
    def check_login(cls):
        """Check login status by making a request."""
        home_page_url = 'https://www.biaozhun.org/member/'
        home_page_response = cls.request(home_page_url)
        if '游客您好请扫描下方二维码登入' in home_page_response.text:
            logger.info('Cached session has expired.')
            return False
        return True

    @classmethod
    def login(cls):
        """Login to bzorg"""
        if not cls.session:
            cls.init_session()

        # try loading cached session info
        if cls.load_cached_session():
            if cls.check_login():
                cls.logged_in = True
                return None
            # cache expired so forget about it
            cls.session.cookies.clear()
            cache_path = get_absolute_path(settings['CACHE_DIR']) / cls.name
            cache_path.unlink()

        logger.info('Logging into www.biaozhun.org...')

        base_url = 'https://open.weixin.qq.com/connect/qrconnect'
        params = {
            'appid': 'wxdccadda88e2d98c6',
            'redirect_uri': 'https://www.biaozhun.cc',
            'response_type': 'code',
            'scope': 'snsapi_login',
            # 'state': encodeURIComponent(state),
        }

        wx_login_page = cls.request(
            base_url,
            params=params,
            headers={'Referer': 'http://www.biaozhun.cc/'},
            )
        assert wx_login_page.ok
        selector = parsel.Selector(wx_login_page.text)

        check_url = selector.re_first(r'var fordevtool = "(\S*)"')
        img_url = urljoin(
            wx_login_page.url,
            selector.xpath(r'//div[@class="wrp_code"]/img/@src').get(),
            )

        show_func = settings['SHOW_WECHAT_LOGIN_CODE_FUNC']
        show_func(cls, img_url)

        cls._cancel_login = False
        status = None
        loops = 0
        while True:
            if cls._cancel_login:
                logger.info('Logging canceled.')
                raise ContentUnavailable('Logging canceled')
            if loops > 40:
                raise ContentUnavailable('Logging timeout')

            time.sleep(1)
            checking_response = cls.request(
                check_url,
                params={'last': status} if status else {},
                timeout=16,
                headers={'Referer': 'https://open.weixin.qq.com/'},
                )
            logger.debug(checking_response.text)

            status, code = re.match(
                r"window.wx_errcode=([0-9]*);window.wx_code='(\S*)';",
                checking_response.text,
                ).groups()
            if status == '408':
                # user hasn't scanned the code
                loops += 5
                continue
            elif status == '404':
                # waiting for confirming on mobile
                loops += 1
                continue
            elif status in ('402', '500'):
                raise ContentUnavailable('Logging timeout')
            elif status == '403':
                raise ContentUnavailable('Logging canceled')
            elif status == '405':
                # success
                break
            else:
                raise ContentUnavailable(f'Unknow status code {code}')

        assert status == '405' and code
        login_url = 'https://www.biaozhun.org/member/wx_login.php'
        params = {
            'code': code,
            'state': 'undefined',
        }
        login_response = cls.request(login_url, params=params)
        assert login_response.ok

        cls.logged_in = True
        cls.cache_session()
        return None

    def get_field(self, name):
        if name in ('pdf',) and not self.logged_in:
            self.login()
        return super().get_field(name)
