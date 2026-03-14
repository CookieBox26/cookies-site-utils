from pathlib import Path
import os
import logging
logger = logging.getLogger(__name__)


class File:
    site_root = None
    domain = ''

    def raise_error(self, msg):
        raise ValueError(f'{msg} {self.path}')

    def __init__(self, path):
        self.path = path
        self.rel_path = os.path.relpath(self.path, File.site_root)
        self.rel_path = Path(self.rel_path ).as_posix()
        self.url = File.domain + self.rel_path

    def write_text(self, text):
        if self.path.exists():
            current_text = self.path.read_text(encoding='utf8')
            if current_text == text:
                logger.debug(f'更新なし {self.rel_path}')
                return
            logger.debug(f'更新あり {self.rel_path}')
        else:
            logger.debug(f'新規作成 {self.rel_path}')
        self.path.write_text(text, newline='\n', encoding='utf8')
