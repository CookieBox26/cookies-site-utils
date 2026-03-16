from cookies_site_utils.builder import ArticlePage
import cookies_site_utils.soup_util as su
from pathlib import Path
import toml
import subprocess
import logging
logger = logging.getLogger(__name__)


class ArticlePageEx(ArticlePage):
    def generate_from_soup(self, soup):
        self.write_text(su.decode_soup(soup))
        self.eval()

    def copy_soup(self, new_title, new_subsite_name_=None):
        soup, text = self.parse()
        new_subsite_name = new_subsite_name_ or self.subsite_name
        su.set_title(soup, new_title, new_subsite_name)
        su.clear_item(soup)
        return soup

    def __init__(self, path, subsite_name=None):
        super().__init__(path, subsite_name)


class ArticleHelper:
    subsite_name = None
    templates = {}

    @classmethod
    def run_job_group(cls, path, jobs):
        ape = ArticlePageEx(path, cls.subsite_name)
        logger.info(ape.rel_path)
        soup = None

        for job in jobs:
            if job.get('skip', False):
                continue
            logger.info('- ' + job['job_type'])

            if job['job_type'] == 'SOUPIFY':
                if soup is None:
                    soup, _ = ape.parse()

            if job['job_type'] == 'COPY_FROM':
                if ape.path.exists():
                    raise ValueError(f'{ape.path} exists.')
                ape_base = ArticlePageEx(job['base_path'], cls.subsite_name)
                soup = ape_base.copy_soup(job['new_title'])
                su.add_categories(soup, job['categories'])

            if job['job_type'] == 'UPDATE_TIMESTAMP':
                if soup is None:
                    soup, _ = ape.parse()
                parent = ape.path.resolve().parent
                if ape.path in ArticleHelper.templates:
                    parent = ArticleHelper.templates[ape.path]
                su.update_timestamp(
                    soup, parent, job['resource'], job['timestamp'],
                )

            if job['job_type'] == 'ADD_REFERENCES':
                if soup is None:
                    soup, _ = ape.parse()
                su.add_references(soup, job['references'])

        if soup is not None:
            ape.generate_from_soup(soup)

        return ape, soup

    @classmethod
    def run(cls, conf_path):
        conf = toml.loads(Path(conf_path).read_text(encoding='utf8'))
        if 'subsite_name' in conf:
            cls.subsite_name = conf['subsite_name']
        if 'templates' in conf:
            for template, parent in conf['templates'].items():
                cls.templates[Path(template)] = Path(parent).resolve()

        soup = None
        for job_group in conf['job_groups']:
            if job_group.get('skip', False):
                continue
            for path_raw in job_group['paths']:
                path = Path(path_raw)
                if '*' in path.name:
                    for path in path.parent.glob(path.name):
                        ape, soup = cls.run_job_group(path, job_group['jobs'])
                else:
                    ape, soup = cls.run_job_group(path, job_group['jobs'])

        if soup is not None:
            if 'text_editor' in conf:
                subprocess.Popen([conf['text_editor'], ape.path.resolve()])
            if 'web_browser' in conf:
                subprocess.Popen([conf['web_browser'], ape.path.resolve()])
