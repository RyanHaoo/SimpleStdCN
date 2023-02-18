from unittest import TestCase

from sscn.utils import NotFound


class NotFoundTestCase(TestCase):
    def test_bool(self):
        self.assertIs(False, bool(NotFound))