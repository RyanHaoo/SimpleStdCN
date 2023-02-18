from ..utils import NotFound
from ..standard import Origin, StandardCode, Status
from ..page import DetailXPathPage, SearchXPathPage, PDFDownloader


class CCSNSearchPage(SearchXPathPage):
    public_fields = ('title', 'title_english', 'status')
    origin_only_fields = ('detail_page_url',)

    search_url = 'http://www.ccsn.org.cn/Xxbz/ForceStandardList.aspx'
    entry_xpath = r'//td[@class="DataListItemStyleCss"]'
    field_xpaths = {
        '_title': (r'.//td[contains(@id,"_mainTd")]/*/text()', NotFound),
        'title_english': (
            r'.//span[contains(@id,"_lbStandardYWName")]/text()', NotFound),
        'detail_page_url': (r'.//td[contains(@id,"_mainTd")]/a/@href', NotFound),
    }

    def get_query_params(self):
        code = str(self.origin.std.code).replace(' ', '')
        return {'keyword': code}

    def is_entry_matching(self, entry):
        title = entry.xpath(
            self.field_xpaths['_title'][0]
            ).get()
        parsed = StandardCode.parse(title)
        return parsed == self.origin.std.code

    def extract_fields(self, base):
        fields = super().extract_fields(base)
        fields['title'] = fields['_title'].partition('〗')[2]
        fields['status'] = Status.VALID
        return fields


class CCSNDetailPage(DetailXPathPage):
    public_fields = (
        'issuance_date', 'implementation_date', 'issued_by',
    )
    origin_only_fields = ('download_page_url',)

    url_field = 'detail_page_url'
    base_node_xpath = r'//table[@class="box_93CCDD"]'
    field_xpaths = {
        '_downloadable': (r'.//a[@href="javascript:ShowFullTextFile();"]', False),
        '_download_page_url_guid': (
            r'//input[@id="ID_ucForceStandardDetail_hfResult"]/@value',
            NotFound),
        'issuance_date': (
            r'.//span[@id="ID_ucForceStandardDetail_lblApprovalDate"]/text()',
            NotFound),
        'implementation_date': (
            r'.//span[@id="ID_ucForceStandardDetail_lblPerformDate"]/text()',
            NotFound),
        'issued_by': (
            r'.//span[@id="ID_ucForceStandardDetail_lblEditSector"]/text()',
            NotFound),
    }

    def extract_fields(self, base):
        fields = super().extract_fields(base)

        download_url_guid = fields['_download_page_url_guid']
        if fields['_downloadable']:
            download_url = self.parse_url(
                '/xxbz/ShowFullText.aspx?Guid='+download_url_guid
            )
            fields['download_page_url'] = download_url
        else:
            fields['download_page_url'] = NotFound
        return fields
            

class CCSNDownloadPage(DetailXPathPage):
    origin_only_fields = ('download_url',)

    url_field = 'download_page_url'
    field_xpaths = {
        'download_url': (r'//form/div/a/@href', NotFound),
    }


class CCSNPDFDownloader(PDFDownloader):
    pass


class CCSNOrigin(Origin):
    index = 'www.ccsn.org.cn'
    name = 'ccsn'
    full_name = '国家工程建设标准化信息网'
    pages = (
        CCSNSearchPage, CCSNDetailPage,
        CCSNDownloadPage, CCSNPDFDownloader,
        )
