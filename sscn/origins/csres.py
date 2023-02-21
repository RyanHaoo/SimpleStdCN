import re
import logging
import parsel

from ..settings import settings
from ..utils import NotFound
from ..standard import Origin, Status, StandardCode
from ..page import DetailXPathPage, SearchXPathPage

# pylint: disable=missing-class-docstring
# no need

logger = logging.getLogger(__name__)

class CSRESSearchPage(SearchXPathPage):
    public_fields = (
        'title', 'issuance_date', 'implementation_date',
        'issued_by', 'status',)
    origin_only_fields = ('detail_page_url',)
    preferred_fields = ('status',)

    search_url = 'http://www.csres.com/s.jsp?'
    entry_xpath = r'//tr[starts-with(@title,"编号")]'
    field_xpaths = {
        '_info': (r'./@title', NotFound),
        '_status': (r'./td[5]/font/text()', NotFound),
        'title': (r'./td[2]/font/text()', NotFound),
        'detail_page_url': (r'./td[1]/a/@href', NotFound),
        'implementation_date': (r'./td[4]/font/text()', NotFound),
    }
    INFO_TEMPLATE = re.compile(
        r'发布部门：(.*)\s发布日期：(.*)\s发布日期：')


    def get_query_params(self):
        std_code = self.origin.std.code
        keyword = str(std_code).replace(' ', '')
        if std_code.year is None:
            keyword += '-'
        # return {'ID': code}
        return {'keyword': keyword}

    def is_entry_matching(self, entry):
        code = entry.xpath(r'./td[1]/a/font/text()').get()
        return str(self.origin.std.code) in code

    def extract_fields(self, content):
        fields = super().extract_fields(content)

        issued_by, issuance_date = self.INFO_TEMPLATE.search(
            fields['_info']).groups()
        fields['issued_by'] = issued_by or NotFound
        fields['issuance_date'] = issuance_date or NotFound

        fields['status'] = {
            '现行': Status.VALID,
            '即将实施': Status.ISSUED,
            '作废': Status.OBSOLETE,
            '废止': Status.ABOLISHED,
        }.get(fields['_status'])

        return fields


class CSRESDetailPage(DetailXPathPage):
    public_fields = (
        'substitute', 'partial_substitutes', 'replaced', 'brief',
        )

    url_field = 'detail_page_url'
    base_node_xpath = r'/html/body/table/form/tr[2]/td/table/tr[1]/td[1]/table'
    field_xpaths = {
        'brief': (
            r'.//td[table/tr/td[text()="标准简介"]]/table[2]/tr/td/text()',
            NotFound),
    }

    def extract_fields(self, content):
        fields = super().extract_fields(content)

        substitutes = []
        partial_substitutes = []
        replaced = []
        subtitute_texts = content.xpath(
            r'.//tr[td/span/strong[text()="替代情况："]]/td[2]//*/text()',
            ).getall()

        statements = ''.join(subtitute_texts).split(';')
        for statement in statements:
            if statement.startswith(('替代', '代替')):
                target = replaced
            elif statement.startswith('被'):
                target = substitutes
            elif statement.startswith('自'):
                target = partial_substitutes
            else:
                target = replaced

            code_matches = StandardCode.CODE_PATTERN.finditer(
                statement)
            for match in code_matches:
                if not (match.group('prefix') and match.group('year')):
                    continue
                target.append(match.group(0))

        fields['substitute'] = substitutes[0] if substitutes else None
        fields['partial_substitutes'] = partial_substitutes or None
        fields['replaced'] = replaced or None

        return fields

class CSRESOrigin(Origin):
    """Source of standard: www.csres.com (工标网)"""
    index = 'www.csres.com'
    name = 'csres'
    full_name = '工标网'
    request_timeout = 10
    pages = (CSRESSearchPage, CSRESDetailPage,)


MANDATORY_MULTIPLIER = 0.5
BASIC_STD_MULTIPLIER = 1.5
BASIC_STD_KEYS = ('通用', '统一')
IMPORTANCE_SUFFIX_SCORE = {
    '标准': 30, '规范': 30,
    '规程': 20, '要求': 20,
    '指南': 10,
    '__others__': 10,
}
CATEGORY_SUFFIX_SCORE = {
    '设计': 30,
    '防火': 25, '制图': 25, '术语': 25,
    '规划': 10,
    '技术': 0,
    '__others__': 10,
}
CATEGORY_SUFFIX_SCORE.update((word, -15) for word in [
    '方法', '施工', '鉴定', '试验', '检验', '维护',
    '验收', '测试', '计算', '法'])
RELEVANCE_MULTIPLIER = {
    'GBJ': 3.0,     # for GB 5xxxx standards
    'GB': 0.8,      # for other GB standards
    'JGJ': 2, 'JG': 1,
    'JCJ': 0.5, 'JC': 0.2,
    'CJJ': 0.5, 'CJ': 0.2,
}
OUTDATED_PENALTY = -2
EXCLUDE_KEYWORDS = ('石油', '化工', '化学', '油气', '铁路', '电厂', '电力', '煤炭',
    '轨道', '通信', '配件', '信息系统', '水利', '水电', '冶金', '纺织', '艇', '000',
    '生产', '采矿', '船', '电气', '交易', '机械', '报文', '桥梁', '储罐',)
EXCLUDE_KEYWORDS_PENALTY = -60

SEPERATORS = r'\(（\[【_\s'
def _compute_standard_sorting_key(code, title):
    base_score = 10
    multiplier = 1

    # standart parts
    if code.part:
        search_subtitle = re.match(f'(.+)[{SEPERATORS}]+'+r'第[0-9]{1,2}部分.*', title)
        multiplier += -0.5
        if search_subtitle:
            title = search_subtitle.group(1)

    # search for edit version
    search_version = re.match(f'(.+)[{SEPERATORS}]+'+r'第?[0-9]{4}.*版.*', title)
    if search_version:
        title = search_version.group(1)
        multiplier += 0.5

    # search for attach
    search_attach = re.match(f'(.+)[{SEPERATORS}]+附.+', title)
    if search_attach:
        title = search_attach.group(1)
        multiplier += 0.2

    # importance level
    for level, value in IMPORTANCE_SUFFIX_SCORE.items():
        if title.endswith(level):
            title = title[:-len(level)]
            base_score += value
            break
    else:
        base_score += IMPORTANCE_SUFFIX_SCORE['__others__']

    # basic keywords
    for key in BASIC_STD_KEYS:
        if title.endswith(key):
            title = title[:-len(key)]
            multiplier += BASIC_STD_MULTIPLIER

    # category
    for cate, value in CATEGORY_SUFFIX_SCORE.items():
        if title.endswith(cate):
            title = title[:-len(cate)]
            base_score += value
            break
    else:
        base_score += CATEGORY_SUFFIX_SCORE['__others__']

    # remaining title length
    length = len(title)
    if length <= 7:
        length_multiplier = 0.2 * (7-len(title))
    else:
        length_multiplier = 0.05 * (7-len(title))
    multiplier += length_multiplier

    # relevance to archi
    if (code.prefix == 'GB'
            and len(code.number) == 5
            and code.number.startswith('5')
            ):
        multiplier += RELEVANCE_MULTIPLIER['GBJ']
        if int(code.number[2:]) < 120:
            multiplier += 0.5
    else:
        multiplier += RELEVANCE_MULTIPLIER[code.prefix[:2]]

    # mandatory
    if code.is_mandatory:
        multiplier += MANDATORY_MULTIPLIER

    # outdated
    if code.year < 2007:
        multiplier += OUTDATED_PENALTY

    # excluded words
    if any(word in title for word in EXCLUDE_KEYWORDS):
        base_score += EXCLUDE_KEYWORDS_PENALTY

    score = max(base_score, 1) * max(multiplier, 0.05)
    # make sure parts are sorted together
    if code.part:
        score -= 0.01*code.part

    return score

def process_query(query):
    """Process a given raw query string to one ready to use."""
    # leave quoted query as-is
    if ((query.startswith('"') and query.endswith('"'))
            or (query.startswith("'") and query.endswith("'"))
            ):
        return query[1:-1]

    try:
        code = StandardCode.parse(query)
    except ValueError:
        pass
    else:
        query = str(code).replace(' ', '') + ('-' if code.year is None else '')
    return query


def compute_standard_sorting_key(standard):
    """Summarize a float value representing the relevance of a standard."""
    code = standard['code']
    title = standard['title']
    try:
        score = _compute_standard_sorting_key(code, title)
    except Exception:    # pylint: disable=broad-exception-caught; not silent
        logger.error('Error summarizing `%s`.', str(code), exc_info=1)
        return -1
    return score

def search_standards(raw_query):
    """Search for standards using `raw_query`.
    
    Returns a sorted list of dicts containing `code`, `title` and `status`
    """
    url = 'http://www.csres.com/s.jsp?'
    entry_xpath = r'//tr[starts-with(@title,"编号")]'

    query = process_query(raw_query)

    search_results = []
    current_page = 1
    while True:
        # make request
        response = CSRESOrigin.request(url, headers={
            'Referer': 'http://www.csres.com',
            'Cookie': 'source=www.csres.com; fz=0; zf=0; xx=1; wss=1',
            }, params={
                'keyword': query.encode('gbk'),
                'pageNum': current_page,
                'SortIndex': 2,
            })
        root = parsel.Selector(text=response.text)
        results = root.xpath(entry_xpath)

        #quick return
        if not results:
            return []

        # filter
        for result in results:
            raw_code = result.xpath(r'./td[1]/a/font/text()').get().strip()
            try:
                parsed = StandardCode.parse(raw_code, fullmatch=True)
            except ValueError:
                continue
            # filter out other fields
            if not any(parsed.prefix.startswith(field_code)
                    for field_code in StandardCode.FIELDS
                    ):
                continue

            search_results.append({
                'code': parsed,
                'title': result.xpath(r'./td[2]/font/text()').get(),
                'status': result.xpath(r'./td[5]/font/text()').get(),
                })

        # next page
        if not root.xpath(r'//a[text()="[下一页]"]'):
            break
        # page limit
        if current_page == 1:
            page_counts = root.xpath(r'//span[@class="hei14"]/text()'
                ).re_first(r'共([0-9]+)页')
            if int(page_counts) > settings['MAX_SEARCH_PAGES']:
                return 'TOO_MANY_RESULTS'

        current_page += 1

    # sort results
    search_results.sort(key=compute_standard_sorting_key, reverse=True)

    for result in search_results:
        result['code'] = str(result['code'])
    return search_results
