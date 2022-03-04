from unittest import TestCase
from unittest.mock import Mock

from sscn.standard import Standard, ResourceNode, Origin


class ResourceNodeTestCase(TestCase):
    def test_get_non_cached_field(self):
        node = ResourceNode(Mock())
        subnode = Mock()
        subnode.get_field = Mock(return_value='bar')
        node.get_subnode = Mock(return_value=subnode)

        bar = node.get_field('bar')
        subnode.get_field.assert_called_once_with('bar')
        self.assertEqual(bar, 'bar')

    def test_get_cached_field(self):
        node = ResourceNode(Mock())
        node.fields['foo'] = 'bar'

        foo = node.get_field('foo')
        self.assertEqual(foo, 'bar')

    def test_update_field(self):
        node = ResourceNode(Mock(), foo='foo')

        # cached field won't be updated without `preferred`
        node.update_field('foo', 'bar')
        self.assertEqual(node.fields['foo'], 'foo')

        # , but will be overwritten with `preferred=True`
        node.update_field('foo', 'bar', preferred=True)
        self.assertEqual(node.fields['foo'], 'bar')

        # non-cached fields
        node.update_field('bar', 'bar')
        self.assertEqual(node.fields['bar'], 'bar')



class StandardTestCase(TestCase):
    def test_get_field_code_not_concret(self):
        code = Mock(is_concret=lambda: False)
        std = Standard(code)
        with self.assertRaises(ValueError):
            std.get_field('foo')

    def test_get_origin(self):
        """
        multiple calls to `get_origin` with the same
        origin class should return the same Origin instance,
        i.e. has the same id.
        """
        std = Standard(Mock())
        origin_cls = Mock()

        origin = std.get_origin(origin_cls)
        origin_cls.assert_called_once_with(std)
        self.assertIs(
            std.get_origin(origin_cls),
            origin,
        )