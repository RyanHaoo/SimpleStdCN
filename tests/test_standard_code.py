from unittest import TestCase

from sscn.standard import StandardCode as StdCode


class StandardCodeTestCase(TestCase):
    def test_parse(self):
        CASES = {
            # prefix - number
            StdCode('50362', 'GB', True): (
                'GB50362', 'GB 50362', 'gb50362',
                'gB-50362', 'Gb_50362',
            ),
            StdCode('50001', 'GB', False): (
                'GBT50001', 'GBT 50001', 'GB T50001',
                'GB/T50001', 'GB/T 50001', 'GB/ T50001',
                'gB_t50001', 'GBt_50001', 'gb_t_50001',
            ),
            StdCode('229', 'JGJ', False): (
                'JGJ/T229', 'JGJT229', 'jgjt 229',
            ),
            StdCode('36', 'JGJ', True): (
                'JGJ36', 'JGJ 36', 'jgJ_36',
            ),
            # number-year
            StdCode('50001', year='2017'): (
                '50001-2017', '50001 2017', '50001_2017',
            ),
            # number
            StdCode('50001'): (
                '50001', ' 50001-', 'T50001-',
            ),
            # part
            StdCode('50001', part=1, year=2021): (
                '50001.1-2021', '50001.1 2021',
            )
        }

        for target, code_strs in CASES.items():
            for code_str in code_strs:
                with self.subTest(target=target, code=code_str):
                    parsed = StdCode.parse(code_str)
                    self.assertEqual(parsed, target)

    def test_new(self):
        code = StdCode(50001, 'GB', False, '2010', '2')
        self.assertEqual(code.number, '50001')   # `number` should be str
        self.assertEqual(code.year, 2010)        # `year` should be int
        self.assertEqual(code.part, 2)           # `part` should be int

    def test_is_concret(self):
        code = StdCode('50001', 'GB', False)
        self.assertFalse(code.is_concret())

        code = code._replace(year=2010)
        self.assertTrue(code.is_concret())

    def test_std_type(self):
        code = StdCode('1', 'GB')
        self.assertEqual(code.std_type, '国家标准')
        code = code._replace(prefix='GBJ')
        self.assertEqual(code.std_type, '工程建设国家标准')

        code = code._replace(prefix='JG')
        self.assertEqual(code.std_type, '建筑工业领域行业标准')
        code = code._replace(prefix='OOJ')
        self.assertEqual(code.std_type, '其他领域工程建设行业标准')

    def test_str(self):
        code = StdCode('50001', 'GB', False, 2010)
        self.assertEqual(str(code), 'GB/T 50001-2010')
        code = code._replace(part=1)
        self.assertEqual(str(code), 'GB/T 50001.1-2010')
        code = code._replace(is_mandatory=True)
        self.assertEqual(str(code), 'GB 50001.1-2010')
