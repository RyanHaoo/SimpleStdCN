import re

from ..utils import NotFound
from ..standard import Origin, Status, StandardCode
from ..page import DetailXPathPage, SearchXPathPage


class CSRESSearchPage(SearchXPathPage):
    public_fields = (
        'title', 'issuance_date', 'implementation_date',
        'issued_by', 'status',)
    origin_only_fields = ('detail_page_url',)
    preferred_fields = ('status',)

    # search_url = 'http://www.csres.com/advanced/s.jsp?STATE=-1&pageSize=45&SortIndex=3&WayIndex=1&searchType=1'
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

    def extract_fields(self, base):
        fields = super().extract_fields(base)

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

    def extract_fields(self, base):
        fields = super().extract_fields(base)

        substitutes = []
        partial_substitutes = []
        replaced = []
        subtitute_texts = base.xpath(
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
    index = 'www.csres.com'
    name = 'csres'
    full_name = '工标网'
    request_timeout = 10
    pages = (CSRESSearchPage, CSRESDetailPage,)