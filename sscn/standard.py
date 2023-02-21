import re
import enum
import logging
from collections import namedtuple

import requests

from sscn.utils import NotFound, HTTPHeaders
from .settings import settings
from .origins import iter_origin_cls
from .exceptions import ContentUnavailable, RequestError


logger = logging.getLogger(__name__)


BaseStdCode = namedtuple(
    'BaseStdCode',
    ('number', 'prefix', 'is_mandatory', 'year', 'part'),
    )

class StandardCode(BaseStdCode):
    """
    Eg:
    GB/T 50001-2017
    —— — ————— ————
    |  |   |    |
    |  |   |    ——— year:        标准批准年号
    |  |   ———————— number:      标准序号
    |  ———————————— mandatory:   强制性。注'T'表示'推荐'，非强制
    ——————————————— prefix:      行业标准代号
    """
    FIELDS = {
        'GB': '国家标准',
        'JC': '建材',
        'CJ': '城镇建设',
        'JG': '建筑工业',
    }
    CODE_PATTERN = re.compile(
        r'(?P<prefix>[A-Z]{2}[A-SU-Z]?)'      # prefix: (GB)T (CJJ)T
        r'[-\_/／\\\s]*(?P<mandatory>T?)'     # mandatory: \(T) /(T) -(T) 
        r'[-\_\s]*(?P<number>[0-9]+)'         # number
        r'(\.(?P<part>[0-9]))?'               # part
        r'[-\_\s]*(?P<year>[0-9]{4}|[5-9][0-9])?' # year
    )

    def __new__(cls, number, prefix=None, is_mandatory=None, year=None, part=None):
        number = str(number)
        year = int(year) if year else None
        part = int(part) if part else None
        return super().__new__(cls, number, prefix, is_mandatory, year, part)

    def __str__(self):
        # pylint: disable=consider-using-f-string
        # too hard to format f-string
        return '{}{} {}{}{}'.format(
            self.prefix,
            '' if self.is_mandatory else '/T',
            self.number,
            f'.{self.part}' if self.part else '',
            f'-{self.year}' if self.year else '',
        )

    def __repr__(self):
        return f'<StandardCode number={self.number}, prefix={self.prefix}, '\
               f'is_mandatory={self.is_mandatory}, year={self.year}, part={self.part}>'

    @classmethod
    def parse(cls, code, fullmatch=False):
        """Parse code into an instance of `StandardCode`.
        
        Raise a ValueError if unable to parse.
        Perform a fullmatch on `code` if `fullmatch` is truthy,
          perform a search otherwise.
        """
        code = code.strip().upper()
        if fullmatch:
            match = cls.CODE_PATTERN.fullmatch(code)
        else:
            match = cls.CODE_PATTERN.search(code)
        if not match:
            raise ValueError(f'"{code}" is not a valid standard code.')

        prefix, mandatory, number, part, year = match.group(
            'prefix', 'mandatory', 'number', 'part', 'year',
        )
        is_mandatory = ('T' not in mandatory) if prefix else None
        if year:
            year = int(year)
            # 95 -> 1995
            year = year+1900 if year < 100 else year
        else:
            year = None

        code_obj = cls(
            prefix=prefix or None,
            is_mandatory=is_mandatory,
            number=number,
            year=year,
            part=part,
            )
        return code_obj

    def is_concret(self):
        """Whether this code represent a specific standard."""
        return all((
            self.prefix is not None,
            self.is_mandatory is not None,
            self.year is not None,
        ))

    @property
    def std_type(self):
        """The category type of the standard."""
        if self.prefix is None:
            return '未知标准'

        # 国标
        if self.prefix == 'GB':
            return '国家标准'
        if self.prefix == 'GBJ':
            return '工程建设国家标准'

        # (工程建设)行业标准
        std_type = self.FIELDS.get(self.prefix[:2], '其他')
        if len(self.prefix) == 3:
            if not self.prefix.endswith('J'):
                return '未知标准'
            return std_type + '领域工程建设行业标准'
        return std_type + '领域行业标准'


class Status(enum.Enum):
    """An enum of status of standards"""
    VALID = '现行'
    ISSUED = '即将实施'
    OBSOLETE = '过时'
    ABOLISHED = '废止'

    def __str__(self):
        return self.value

    def is_active(self):
        """Wheteher a standard with this status is regarded as `active`"""
        return self in {self.VALID, self.ISSUED}


class ResourceNode:
    """
    Base class for `Standard` and `Origin`. Can
    
    """
    def __init__(self, **kwargs):
        self.fields = kwargs
        self.subnodes = {}

    @classmethod
    def iter_subnode_cls(cls, field_name):
        """Iters from subnode classes responsible for field `field_name`"""
        raise NotImplementedError()

    def update_field(self, name ,field, preferred=False):
        """Cache a field in the instance. Overwrite exsiting field
        if set `preferred=True`.
        """
        if (name not in self.fields
                or preferred):
            self.fields[name] = field
            return True
        return False

    def get_field(self, name):
        """Require a field. Return the cached value or ask its
        subnodes for the value.
        """
        logger.debug('%r: getting field "%s"...', self, name)
        if name in self.fields:
            logger.debug('%r: use cached value.', self)
            return self.fields[name]

        cls_iter = self.iter_subnode_cls(name)
        for cls in cls_iter:
            subnode = self.get_subnode(cls)
            logger.debug('dispatch to %r', subnode)
            try:
                field = subnode.get_field(name)
            except ContentUnavailable:
                logger.debug(
                    '%r: catched ContentUnavailable,'
                    'continue', self)
                continue
            if field is not NotFound:
                return field
            continue

        # none of the subnodes found the field
        self.fields[name] = NotFound
        logger.debug('%r: field "%s" not found.', self, name)
        return NotFound

    def get_subnode(self, cls):
        """Return the subnode instance of class `cls` on this node.
        """
        # Each subnode has only one instance per ResourceNode class
        instance = self.subnodes.setdefault(cls, cls(self))
        return instance


class Standard(ResourceNode):
    """Standard class that could search for and cache its fields."""
    def __init__(self, code, **kwargs):
        self.code = code
        self.concret = self.code.is_concret()
        super().__init__(**kwargs)

    def __str__(self):
        code = str(self.code)
        if self.concret:
            title = self.fields.get('title')
            if title:
                return f'{code} {title}'
            return code
        return repr(self)

    def __repr__(self):
        return f'<Standard code="{self.code}">'

    @classmethod
    def iter_subnode_cls(cls, field_name):
        return iter_origin_cls()

    def as_file_name(self, suffix='pdf'):
        """Make a filename for this standard to store."""
        filename_table = str.maketrans({
            '/': '-',
            '-': '_',
            ' ': '_'})
        if not self.concret:
            raise TypeError(
                'Can only get file name of a concret standard instance.')
        name = str(self).translate(filename_table)
        return f'{name}.{suffix}'

    def get_field(self, name):
        if not self.concret:
            raise TypeError(
                'Can only get fields from a concret standard instance.'
                )
        return super().get_field(name)


class Origin(ResourceNode):
    """Abstract Origin class for subclassing."""
    # basic info
    index = None
    name = None
    full_name = None

    # settings
    pages = ()
    request_timeout = None

    # class data
    session = None
    _public_fields = None
    _preferred_fields = None

    def __init__(self, std, **kwargs):
        self.std = std
        super().__init__(**kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__} std="{self.std.code}">'

    @classmethod
    def _get_page_fields(cls, name):
        """Underlying func of `fields()` and `preferred_fields()`"""
        field_set = set()
        for page in cls.pages:
            fields = getattr(page, name)
            fields = [f for f in fields
                if f not in page.origin_only_fields
                ]    # filter public fields
            field_set.update(fields)
        return frozenset(field_set)

    @classmethod
    @property
    def public_fields(cls):
        """All public fields registered by pages."""
        if cls._public_fields is None:
            cls._public_fields = cls._get_page_fields(
                'public_fields')
        return cls._public_fields

    @classmethod
    @property
    def preferred_fields(cls):
        """All public preferred fields registered by pages."""
        if cls._preferred_fields is None:
            cls._preferred_fields = cls._get_page_fields(
                'preferred_fields')
        return cls._preferred_fields

    @classmethod
    def iter_subnode_cls(cls, field_name):
        """Iters through all Page class responsible for `field_name`.
        
        Page classes are itered in the order of `cls.pages`,
        except that pages with `field_name` set in its `preferred_fields`
        are granted to be itered first.
        """
        for page_cls in cls.pages:
            if field_name in page_cls.preferred_fields:
                yield page_cls

        for page_cls in cls.pages:
            if (field_name in page_cls.public_fields
                or field_name in page_cls.origin_only_fields
                ):
                yield page_cls

    @classmethod
    def init_session(cls):
        """Init a Session object preserving the http connction.
        """
        session = requests.session()
        session.headers.update(HTTPHeaders())
        logger.info('Initiated session for origin `%s`.', cls.__name__)
        cls.session = session
        return session

    @classmethod
    def request(cls, url, method='GET', retry=0, timeout=None, **kwargs):
        """Make a request with a max retry of MAX_PAGE_RETRY.
        """
        session = cls.session or cls.init_session()
        logger.info('Requesting `%s`. %s',
            url,
            f'(retry={retry})' if retry else '',
            )
        timeout = timeout or cls.request_timeout or settings['TIMEOUT']

        try:
            response = session.request(method, url, timeout=timeout, **kwargs)
        except requests.Timeout as err:
            logger.info('Request time out.')
            # retry if time out
            if retry >= settings['REQUEST_MAX_RETRY']:
                raise RequestError('Request time out.') from err
            return cls.request(
                url, method=method, retry=retry+1, **kwargs)
        except requests.HTTPError as err:
            logger.info(
                'Request failed: %s %s',
                err.response.status_code,
                err.response.reason)
            raise

        return response
