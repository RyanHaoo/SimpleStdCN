import io
import re

import rarfile

from ..utils import NotFound
from ..exceptions import ContentNotFound
from ..standard import Origin, StandardCode
from ..page import DetailXPathPage, SearchXPathPage, PDFDownloader

# pylint: disable=missing-class-docstring
# no need

class BzkoSearchPage(SearchXPathPage):
    origin_only_fields = ('standard_id',)

    search_url = 'http://www.bzko.com/search.aspx'
    entry_xpath = r'//div[@class="c_content"]/li/a'

    def get_query_params(self):
        code = self.origin.std.code
        keyword = f'{code.number}{f".{code.part}" if code.part else ""}-{code.year}'
        return {'keyword': keyword}

    def is_entry_matching(self, entry):
        full_title = entry.xpath('./text()').get()
        code = StandardCode.parse(full_title)
        target = self.origin.std.code
        return (
            code.prefix == target.prefix
            and code.number == target.number
            and code.year == target.year
            # prefix is wrongly documented often
        )

    def extract_fields(self, content):
        detail_url = content.xpath('./@href').get()
        standard_id = re.search(
            r'/std/([0-9]*)\.html',
            detail_url).group(1)
        assert standard_id

        return {'standard_id': standard_id}


class BzkoDownloadPage(DetailXPathPage):
    origin_only_fields = ('download_url',)

    field_xpaths = {
        'download_url': (
            r'//form[@id="ShowDownloadUrl"]//table//a/@href',
            NotFound),
    }

    def get_url(self):
        base_url = 'http://www.bzko.com/Common/ShowDownloadUrl.aspx?id={}'
        std_id = self.origin.get_field('standard_id')
        url = base_url.format(std_id)
        return url


class BzkoPDFDownloader(PDFDownloader):
    def parse_response(self, response):
        archive = rarfile.RarFile(
            io.BytesIO(response.content))
        for file_info in archive.infolist():
            if not file_info.filename.endswith('.pdf'):
                continue
            pdf = archive.open(file_info)
            return pdf.read()
        raise ContentNotFound()


class BzkoOrigin(Origin):
    """Source of standard: www.bzko.com (标准库)"""
    index = 'www.bzko.com'
    name = 'bzko'
    full_name = '标准库'
    pages = (BzkoSearchPage, BzkoDownloadPage, BzkoPDFDownloader)
