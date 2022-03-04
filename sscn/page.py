import parsel
import logging
from sys import exc_info
from traceback import format_exception
from urllib.parse import urljoin

from .settings import settings
from .utils import NotFound
from .exceptions import (
    ContentNotFound, RequestError, ContentUnavailable,
    FieldNotRegistered, StandardNotFound,)


logger = logging.getLogger(__name__)


class Page:
    """Base Page class."""
    public_fields = ()
    origin_only_fields = ()
    preferred_fields = ()
    referer = None

    def __init__(self, origin):
        self.origin = origin
        self.request_errored = 0
        self.success = None
        
    def __repr__(self):
        return '<{} code={}>'.format(
            self.__class__.__name__,
            self.origin.std.code)

    def get_field(self, name):
        """Fetch and return field `name`.
        """
        logger.debug(
            '{!r}: getting field "{}"...'.format(self, name))

        # this page has already been fetched
        if self.success is not None:
            # non-NotFound fields must have been cached by Origin or Standard
            if self.success is True:
                raise ContentNotFound()

            # don't retry if has failed because of non-network issue or
            #  has retryed too many times
            if (not self.request_errored
                or self.request_errored >= settings['MAX_PAGE_RETRY']
                ):
                raise ContentUnavailable()

        try:
            fields = self.fetch()
        except RequestError as e:
            self.success = False
            self.request_errored += 1
            self.response = e
            raise
        except ContentUnavailable as e:
            raise e
        except Exception:
            logger.error('Page {1} errored:{0}'.format(
                (' '*4).join(
                    ['\n']+format_exception(*exc_info())
                    ),
                self))
            self.success = False
            raise ContentUnavailable()
        else:
            self.success = True
            self.request_errored = 0

        logger.debug('{!r}: field "{}" fetched.'.format(
            self, name, fields[name]))
        return fields[name]

    def fetch(self):
        """Fetch the remote page and return extracted fields.
        """
        url = self.get_url()
        if not url:
            raise ContentNotFound()
        response = self.request(url)
        content = self.parse_response(response)
        fields = self.extract_fields(content)

        self.post_fetch(fields)
        return fields

    def post_fetch(self, fetched_fields):
        """Update `fetched_fields` to origin and std.
        
        Every registered fields must be in `fetched_fields`
        and unless starting with '_', no other fields should
        be in `fetched_fields`.
        """
        _fetched_fields = fetched_fields.copy()

        # cycle through registered fields
        for field_name in self.public_fields + self.origin_only_fields:
            try:
                field = _fetched_fields.pop(field_name)
            except KeyError:
                raise TypeError(
                    'Field `{}` is registered in {} but'
                    "its `.fetch()` didn't return it.".format(
                        field_name, self.__class__
                    ))
            
            preferred = field_name in self.preferred_fields
            receiver = (self.origin
                if field_name in self.origin_only_fields
                else self.origin.std)
            receiver.update_field(
                field_name,
                field,
                preferred=preferred,
                )

        # raise if there are remaining unregistered fields
        #  which don't starts with '_'
        for name in _fetched_fields.keys():
            if name.startswith('_'):
                continue
            raise FieldNotRegistered(
                name, self.__class__)
        return None

    def request(self, *args, **kwargs):
        if self.referer:
            kwargs.setdefault('headers', {}).update({
                'Referer': self.referer
            })
        response = self.origin.request(*args, **kwargs)
        self.response = response
        return response

    def get_url(self):
        raise NotImplementedError()

    def extract_fields(self, content):
        raise NotImplementedError()

    def parse_response(self, response):
        return response.text

    def parse_url(self, url):
        if url:
            parsed = urljoin(self.response.url, url)
            return parsed
        return url


class PDFDownloader(Page):
    public_fields = ('pdf',)
    url_field = 'download_url'

    def get_url(self):
        url = self.origin.get_field(self.url_field)
        if not url:
            raise ContentNotFound()
        return url
    
    def post_fetch(self, fetched_fields):
        # Disable field cache
        return None

    def parse_response(self, response):
        return response.content

    def extract_fields(self, content):
        return {'pdf': content}


class XPathPage(Page):
    """
    field_xpaths: {
        'field_name': (
            'xpath_query',
            default),
        }
    """
    base_node_xpath = None
    field_xpaths = None

    def get_base_node(self, html):
        root = parsel.Selector(text=html)
        if not self.base_node_xpath:
            return root

        base = root.xpath(self.base_node_xpath)
        return base

    def parse_response(self, response):
        html = super().parse_response(response)
        base = self.get_base_node(html)
        return base

    def extract_fields(self, base):
        if not self.field_xpaths:
            return {}

        fields = {}
        for name, args in self.field_xpaths.items():
            query, default = args
            field = base.xpath(query).get(NotFound)
            if (field is not NotFound
                    and not field):
                field = default
            
            if name.endswith('url') and field:
                field = self.parse_url(field)
            fields[name] = field
        return fields


class DetailXPathPage(XPathPage):
    url_field = None

    def get_url(self):
        url = self.origin.get_field(self.url_field)
        return url


class SearchXPathPage(XPathPage):
    search_url = None
    entry_xpath = None

    def get_entries(self, base):
        entries = base.xpath(self.entry_xpath)
        return entries

    def get_entry(self, base):
        entries = self.get_entries(base)
        matchings = [e for e in entries if self.is_entry_matching(e)]
        if not matchings:
            logger.info('Can not find {} in origin `{}`.'.format(
                self.origin.std.code,
                self.origin.name,
            ))
            raise StandardNotFound()
        return matchings[0]

    def get_url(self):
        return self.search_url

    def get_query_params(self):
        raise NotImplementedError()

    def request(self, url, **kwargs):
        query_params = self.get_query_params()
        if 'params' in kwargs:
            kwargs['params'].update(query_params)
        else:
            kwargs['params'] = query_params
        return super().request(url, **kwargs)

    def is_entry_matching(self, entry):
        raise NotImplementedError()

    def get_base_node(self, html):
        base = super().get_base_node(html)
        entry = self.get_entry(base)
        return entry
