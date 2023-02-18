import cmd
import os
import sys
import logging
from pathlib import Path
from argparse import ArgumentParser

from sscn.utils import NotFound
from sscn.standard import StandardCode, Standard


LOGGING_CONFIG = {
    'format': '%(asctime)s [%(levelname)s]: %(message)s',
    'datefmt': '%m/%d/%Y %H:%M:%S',
    }


class SSCNCLI(cmd.Cmd):
    intro = 'Welcome to SimpleStdCN\n'
    prompt = '> '

    def __init__(self, *, download_dir, debug=False):
        self.download_dir = download_dir
        self.std = None

        if debug:
            logging.basicConfig(
                level=logging.DEBUG,
                **LOGGING_CONFIG)
        else:
            logging.basicConfig(
                filename=Path(sys.path[0])/'./sscn.log',
                filemode='w',
                level=logging.INFO,
                **LOGGING_CONFIG)
        self.set_prompt()
        super().__init__()

    def set_prompt(self):
        if self.std:
            self.prompt = str(self.std.code) + ' > '
        else:
            self.prompt = '> '

    def print(self, *args, **kwargs):
        print(*args, **kwargs)

    def precmd(self, line):
        line = line.strip()
        if self.std:
            if not (
                line.startswith('get ')
                or line.startswith('set ')
                or line == 'download'
                or line == 'unset'
                or line == 'exit'
                ):
                line = 'get ' + line
        return line

    def do_set(self, arg):
        """Set standard."""
        try:
            code = StandardCode.parse(arg)
        except Exception:
            self.print('Not valid.')
            return None

        if not code.is_concret():
            self.print('Not concret.')
            return None
        self.print('Standard set: {}.'.format(code))
        self.std = Standard(code)
        self.set_prompt()
    
    def do_unset(self, arg):
        """Unset current standard."""
        self.std = None
        self.set_prompt()

    def do_get(self, arg):
        """Get field of current standard."""
        if not self.std:
            self.print('No standard set.')
            return None

        field = self.std.get_field(arg)
        self.print(field)
        return None

    def do_download(self, arg):
        """Download current standard."""
        if not self.std:
            self.print('No standard set.')
            return None

        file_name = self.std.as_file_name()
        file_path = self.download_dir / file_name
        if file_path.exists():
            self.print(
                '"{}" is already in the download '
                'directory "{}"!'.format(
                    file_name, self.download_dir
                ))
            return None

        content = self.std.get_field('pdf')
        if content is NotFound:
            self.print('Can not found file.')
            return None

        with open(file_path, 'wb') as f:
            f.write(content)
        self.print('Successfully download to {}.'.format(
            file_path
        ))
        return None

    def do_exit(self, arg):
        """Exit program."""
        self.print('Bye.')
        return True


argparser = ArgumentParser(
    description='CommandLineInterface of SimpleStdCN.'
)
argparser.add_argument('--debug', action='store_true')
argparser.add_argument(
    '-d', '--directory', default='./download/', type=Path,
    dest='download_dir')


if __name__ == '__main__':
    args = vars(argparser.parse_args())

    download_dir = args['download_dir']
    if not download_dir.is_absolute():
        download_dir = sys.path[0] / download_dir
    if not download_dir.is_dir():
        os.mkdir(download_dir)

    args['download_dir'] = download_dir

    SSCNCLI(**args).cmdloop()
