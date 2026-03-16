from pathlib import Path
import os
import logging
logger = logging.getLogger(__name__)


class File:
    site_root = None
    domain = ''

    def raise_error(self, msg):
        raise ValueError(f'{msg} {self.path}')

    def log(self, msg):
        logger.log(self.log_level, msg)

    def __init__(self, path, verbose=False):
        if not isinstance(path, Path):
            path = Path(path)
        self.path = path
        self.log_level = logging.INFO if verbose else logging.DEBUG
        self.rel_path = os.path.relpath(self.path, File.site_root)
        self.rel_path = Path(self.rel_path ).as_posix()
        self.url = File.domain + self.rel_path

    def write_text(self, text):
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)
        if self.path.exists():
            current_text = self.path.read_text(encoding='utf8')
            if current_text == text:
                self.log(f'更新なし {self.rel_path}')
                return
            self.log(f'更新あり {self.rel_path}')
        else:
            self.log(f'新規作成 {self.rel_path}')
        self.path.write_text(text, newline='\n', encoding='utf8')
