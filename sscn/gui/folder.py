import logging
import operator

import yaml

from sscn.standard import StandardCode


logger = logging.getLogger(__name__)


def load_dir_tree(path, filename_parser, files_sorting_key=None):
    subdirs = []
    files = []
    for child in path.iterdir():
        if child.is_dir():
            subdirs.append(
                (child.stem, load_dir_tree(child, filename_parser, files_sorting_key))
                )
        else:
            parsed_name = filename_parser(child.name)
            if parsed_name is False:
                continue
            files.append(parsed_name)

    subdirs.sort(key=operator.itemgetter(0))
    files.sort(key=files_sorting_key)
    subdirs.extend(files)
    return subdirs


def load_folder_tree(path):
    def parser(name):
        if name.endswith('.yaml') or name.endswith('.yml'):
            return name
        else:
            return False

    return load_dir_tree(path, parser)


def load_downloaded_tree(path):
    def parser(name):
        name = name.replace('_', ' ')
        if not name.endswith('.pdf'):
            return False
        name = name.partition('.')[0]

        match = StandardCode.CODE_PATTERN.match(name)
        if not match:
            return False
        code = StandardCode.parse(name)
        title = name[match.end(0):].strip()
        return {'code': str(code), 'title': title}

    return load_dir_tree(path, parser, operator.itemgetter('code'))


def _parse_yaml_tree(nodes):
    subtrees = []
    end_nodes = []
    for node in nodes:
        if isinstance(node, dict):
            items = node.items()
            assert len(items) == 1

            name, subtree = list(items)[0]
            subtrees.append(
                (name, _parse_yaml_tree(subtree) if subtree else [])
                )
        else:
            node = node.strip()
            match = StandardCode.CODE_PATTERN.match(node)
            assert match is not None

            code = match.group(0)
            title = node[match.end(0):].strip()

            end_nodes.append({'code': code, 'title': title})
            # assert isinstance(node, str)
            # end_nodes.append(node.strip())
    
    subtrees.extend(end_nodes)
    return subtrees

def load_folder_file(path):
    with open(path, encoding='UTF8') as f:
        tree = yaml.safe_load(f)

    assert isinstance(tree, list)
    return _parse_yaml_tree(tree)
