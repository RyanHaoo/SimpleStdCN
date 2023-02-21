import cmd
import os
import sys
import logging
from pathlib import Path
from argparse import ArgumentParser

from sscn.utils import NotFound, get_absolute_path
from sscn.standard import StandardCode, Standard


LOGGING_CONFIG = {
    'format': '%(asctime)s [%(levelname)s]: %(message)s',
    'datefmt': '%m/%d/%Y %H:%M:%S',
    }


class SSCNCLI(cmd.Cmd):
    """CLI interface"""
    # pylint: disable=unused-argument
    # an `arg` is still required for actions that don't use it

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
        """Setting the cli prompt depending on the state"""
        if self.std:
            self.prompt = str(self.std.code) + ' > '
        else:
            self.prompt = '> '

    def print(self, *args, **kwargs):
        """Print something to the stdout."""
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
        except ValueError:
            self.print('Not valid.')
            return None

        if not code.is_concret():
            self.print('Not concret.')
            return None
        self.print(f'Standard set: {code}.')
        self.std = Standard(code)
        self.set_prompt()
        return None

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
                f'"{file_name}" is already in the download '
                f'directory "{self.download_dir}"!')
            return None

        content = self.std.get_field('pdf')
        if content is NotFound:
            self.print('Can not found file.')
            return None

        with open(file_path, 'wb') as file:
            file.write(content)
        self.print(f'Successfully download to {file_path}.')
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
    parsed_args = vars(argparser.parse_args())

    absolute_download_dir = get_absolute_path(parsed_args['download_dir'])
    if not absolute_download_dir.is_dir():
        os.mkdir(absolute_download_dir)
    parsed_args['download_dir'] = absolute_download_dir

    SSCNCLI(**parsed_args).cmdloop()
