import sys
import random
from pathlib import Path


USER_AGENTS = (
    'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, '
        'like Gecko) Chrome/99.0.7113.93 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
        'like Gecko) Chrome/91.0.4472.19 Safari/537.36 Edg/91.0.864.11',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0)'
        ' Gecko/20100101 Firefox/85.0',
)


class HTTPHeaders(dict):
    """A dict subclass that automaticlly contains
    some basic HTTP headers when initialized
    """
    def __init__(self, *args, **kwargs):
        self.update({
            'Accept': 'text/html,*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'User-Agent': random.choice(USER_AGENTS),
        })
        super().__init__(*args, **kwargs)


class _NotFoundType:
    """Represent a value that could not be found.
    
    Use initialized `NotFound` instead of make new instances
    """
    def __bool__(self):
        return False

    def __str__(self):
        return '未找到'

NotFound = _NotFoundType()


def get_absolute_path(path):
    """Turn any `path` into a working absolute `Path` instance.
    
    Works either in code environment or packed environment.
    """
    path = path if isinstance(path, Path) else Path(path)
    if path.is_absolute():
        return path

    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(sys.path[0])
    return base_dir / path
