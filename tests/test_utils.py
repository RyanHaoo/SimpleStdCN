from unittest import TestCase

from sscn.utils import NotFound


class NotFoundTestCase(TestCase):
    """Testcase for class `NotFound`"""
    def test_bool(self):
        """should be falsy"""
        self.assertIs(False, bool(NotFound))
