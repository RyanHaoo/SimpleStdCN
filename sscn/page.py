import logging
from urllib.parse import urljoin

import parsel

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
        self.response = None

    def __repr__(self):
        return f'<{self.__class__.__name__} code={self.origin.std.code}>'

    def get_field(self, name):
        """Fetch and return field `name`.
        """
        logger.debug('%r: getting field "%s"...', self, name)

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
        except RequestError as err:
            self.success = False
            self.request_errored += 1
            self.response = err
            raise
        except ContentUnavailable as err:
            raise err
        except Exception as err:
            logger.error('Page %s errored:', self, exc_info=1)
            self.success = False
            raise ContentUnavailable() from err

        self.success = True
        self.request_errored = 0

        logger.debug(
            '%r: field "%s" fetched: `%s`.', self, name, fields[name]
            )
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
            except KeyError as err:
                raise TypeError(
                    f'Field `{field_name}` is registered in {self.__class__}'
                    "but its `.fetch()` didn't return it."
                ) from err

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
        """Perform a http request using its `origin`."""
        if self.referer:
            kwargs.setdefault('headers', {}).update({
                'Referer': self.referer
            })
        response = self.origin.request(*args, **kwargs)
        self.response = response
        return response

    def get_url(self):
        """Get the url to request this page.
        
        Implement by subclass.
        """
        raise NotImplementedError()

    def extract_fields(self, content):
        """Extract value of registered fields from requested `content`.
        
        Implement by subclass.
        """
        raise NotImplementedError()

    def parse_response(self, response):
        """Parse the raw http `response` to its content."""
        return response.text

    def parse_url_field(self, url_field):
        """Make sure extracted url is complete by joining with the request url."""
        parsed = urljoin(self.response.url, url_field)
        return parsed


class PDFDownloader(Page):
    """Abstract page class for downloading field `pdf`."""
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
    """Abstrat page class that uses xpaths to extract fields.

    base_node_xpath: an xpath str as the root of further searchings
    field_xpaths: a dict containing `xpath_query` strings for each `field_name`
                {
                    'field_name': ('xpath_query', default),
                    ...
                }
    """
    base_node_xpath = None
    field_xpaths = None

    def get_url(self):
        raise NotImplementedError()

    def get_base_node(self, html):
        """Get the base xpath node from html content."""
        root = parsel.Selector(text=html)
        if not self.base_node_xpath:
            return root

        base = root.xpath(self.base_node_xpath)
        return base

    def parse_response(self, response):
        """Parse raw http response into a root xpath node."""
        html = super().parse_response(response)
        base = self.get_base_node(html)
        return base

    def extract_fields(self, content):
        """Perform xpath search for fields in `field_xpaths` on root `base`."""
        if not self.field_xpaths:
            return {}

        fields = {}
        for name, args in self.field_xpaths.items():
            query, default = args
            field = content.xpath(query).get(NotFound)
            if (field is not NotFound
                    and not field):
                field = default

            if name.endswith('url') and field:
                field = self.parse_url_field(field)
            fields[name] = field
        return fields


class DetailXPathPage(XPathPage):
    """Abstract page class to get detailed fields of a standard."""
    url_field = None

    def get_url(self):
        url = self.origin.get_field(self.url_field)
        return url


class SearchXPathPage(XPathPage):
    """Abstract page class to search for a standard."""
    search_url = None
    entry_xpath = None

    def get_entries(self, base):
        """Get all entries from the root xpath node `base`
        of research request.
        """
        entries = base.xpath(self.entry_xpath)
        return entries

    def is_entry_matching(self, entry):
        """Determine whether search result `entry`
        matches with the required standard.
        
        Implement by subclass.
        """
        raise NotImplementedError()

    def get_entry(self, base):
        """Get the matching entry from the root xpath node `base`
        of research request."""
        entries = self.get_entries(base)
        matchings = [e for e in entries if self.is_entry_matching(e)]
        if not matchings:
            logger.info(
                'Can not find %s in origin `%s`.',
                self.origin.std.code,
                self.origin.name,
            )
            raise StandardNotFound()
        return matchings[0]

    def get_base_node(self, html):
        base = super().get_base_node(html)
        entry = self.get_entry(base)
        return entry

    def get_url(self):
        return self.search_url

    def get_query_params(self):
        """Get the params for performing the GET searching request.
        
        Implement by subclass.
        """
        raise NotImplementedError()

    def request(self, *args, **kwargs):
        query_params = self.get_query_params()
        if 'params' in kwargs:
            kwargs['params'].update(query_params)
        else:
            kwargs['params'] = query_params
        return super().request(*args, **kwargs)
