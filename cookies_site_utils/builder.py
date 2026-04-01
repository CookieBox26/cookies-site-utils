from cookies_site_utils.core import File
from pathlib import Path
import fnmatch
import os
import re
from bs4 import BeautifulSoup
from shirotsubaki.element import Element as Elm
from datetime import datetime
from jinja2 import Template
import toml
from contextlib import contextmanager
import logging
logger = logging.getLogger(__name__)


class PageCharCounter:
    """
    ページの文字数をカウントします
    - インライン要素の閉じタグ直後の1つ以上の改行を1つの改行とみなします
    - ブロック要素の閉じタグ直後の1つ以上の改行を無視します
    """
    def __init__(self):
        self.closing_tag = re.compile(r'(</[^>]+>)\n+')
        self.inline_tags = {'span', 'a', 'code'}
        self.void_tags = {'br', 'hr'}
        self.void_tag = re.compile(r'(<(br|hr)\s*/?>)\n+')

    def _closing_tag_repl(self, match):
        tag = match.group(1)
        if tag[2:-1].strip() in self.inline_tags:
            return tag + '\n'
        return tag

    def _void_tag_repl(self, match):
        return match.group(1)

    def normalize(self, text):
        text = self.closing_tag.sub(self._closing_tag_repl, text)
        text = self.void_tag.sub(self._void_tag_repl, text)
        return text

    def __call__(self, text):
        return len(self.normalize(text))


class Page(File):
    last_counts = None
    force_keep_timestamp = False

    @classmethod
    def load_last_counts(cls, last_counts_path):
        if not last_counts_path:
            logger.warning('ページ最終更新日管理ファイルが指定されていません')
            return
        if not last_counts_path.is_file():
            cls.last_counts = {}
            return
        with open(last_counts_path, encoding='utf8') as f:
            pages = toml.load(f)['pages']
            cls.last_counts = {page['rel_path']: page for page in pages}

    @classmethod
    def dump_last_counts(cls, last_counts_path):
        if not last_counts_path:
            return
        with open(last_counts_path, mode='w', encoding='utf8', newline='\n') as f:
            toml.dump({'pages': [v[1] for v in sorted(cls.last_counts.items())]}, f)

    def get_file_timestamp(self):
        return datetime.fromtimestamp(self.path.stat().st_mtime).strftime('%Y-%m-%d')

    def set_timestamp(self, count=-1):
        if Page.last_counts is None:
            self.timestamp = self.get_file_timestamp()
            return

        last_count = 0
        if self.rel_path in Page.last_counts:
            last_count = Page.last_counts[self.rel_path]['count']
        else:
            Page.last_counts[self.rel_path] = {'rel_path': self.rel_path}
        sign = ' '
        if not Page.force_keep_timestamp:
            if count == last_count:  # 文字数が前回と一致であれば前回タイムスタンプ
                self.timestamp = Page.last_counts[self.rel_path]['timestamp']
            else:  # 文字数が前回と不一致であればファイルタイムスタンプ
                sign = 'U' if (last_count > 0) else 'A'
                self.timestamp = self.get_file_timestamp()
                Page.last_counts[self.rel_path]['timestamp'] = self.timestamp
                Page.last_counts[self.rel_path]['count'] = count
        else:  # タイムスタンプを保つモード (メンテナンス用)
            # 前回のタイムスタンプがあれば取りなければファイルタイムスタンプ
            self.timestamp = Page.last_counts[self.rel_path].get('timestamp', None)
            if self.timestamp is None:
                sign = 'A'
                self.timestamp = self.get_file_timestamp()
                Page.last_counts[self.rel_path]['timestamp'] = self.timestamp
            else:
                count_cur = Page.last_counts[self.rel_path]['count']
                sign = 'K' if (count != count_cur) else ' ' 
            Page.last_counts[self.rel_path]['count'] = count
        logger.info(' '.join([
            self.timestamp, sign, self.title,
            ('' if (sign == ' ') else f'({last_count} --> {count})'),
        ]))

    def eval_soup(self, soup):
        self.title = soup.find('h1').get_text()
        if self.subsite_name is not None:
            page_title = soup.title.get_text()
            if self.is_index:
                if page_title != f'{self.subsite_name}':
                    self.raise_error('title タグがサブサイト名でない')
            else:
                if page_title != f'{self.title} - {self.subsite_name}':
                    self.raise_error('title タグが h1 タグ + サブサイト名でない')
        if not self.strict_check:
            return
        for tag in soup.find_all(True):
            if tag.has_attr('style'):
                self.raise_error('インラインスタイルがある')
        for a in soup.find_all('a'):
            if a.has_attr('target'):
                self.raise_error('a タグに target 属性がある')

    def parse(self):
        text = self.path.read_text(encoding='utf8')
        soup = BeautifulSoup(text, 'html.parser')
        return soup, text

    def eval(self, return_soup=False):
        soup, text = self.parse()
        self.eval_soup(soup)
        count = self.counter(text)
        self.set_timestamp(count=count)
        if return_soup:
            return soup

    def __init__(self, path, subsite_name=None, strict_check=True):
        super().__init__(path)
        self.subsite_name = subsite_name
        self.strict_check = strict_check
        self.is_index = (type(self).__name__ == 'IndexPage')
        self.counter = PageCharCounter()

    def generate_from_template(self, template, context):
        rendered = template.render(context) + '\n'
        self.write_text(rendered)
        self.eval()

    def as_anchor(self, source_path, with_ts=False):
        rel_path_from_source = os.path.relpath(self.path, source_path.parent)
        rel_path_from_source = Path(rel_path_from_source).as_posix()
        elm_a = Elm('a', self.title).set_attr('href', rel_path_from_source)
        elm_a = str(elm_a).replace('\n', '')
        if not with_ts:
            return elm_a
        elm_ts = Elm('span', self.timestamp).set_attr('class', 'index-ts')
        elm_ts = str(elm_ts).replace('\n', '')
        return f'{elm_a} {elm_ts}'

    def as_xml_url(self):
        priority = 1.0 if self.is_index else 0.5
        return '\n'.join([
            '<url>',
            f'<loc>{self.url}</loc>',
            f'<lastmod>{self.timestamp}</lastmod>',
            '<changefreq>monthly</changefreq>',
            f'<priority>{priority}</priority>',
            '</url>',
        ])

    @staticmethod
    def as_ul_of_links(pages, source_path, with_ts=False, n_max=None):
        ul = Elm('ul')
        for page in pages:
            ul.append(Elm('li', page.as_anchor(source_path, with_ts)))
            if (n_max is not None) and (len(ul.inner) >= n_max):
                break
        return str(ul)


class CategoryPage(Page):
    additional_context = {}

    def __init__(self, cat_name, path, subsite_name):
        super().__init__(path, subsite_name)
        self.cat_name = cat_name
        self.articles = []
        self.articles_with_subcat = {}

    def generate_from_template(self, template):
        self.articles.sort(key=lambda a: a.title.lower())
        list_article = Page.as_ul_of_links(
            self.articles, self.path, with_ts=True,
        )
        n_articles = len(self.articles)
        if len(self.articles_with_subcat) > 0:
            self.articles_with_subcat = list(sorted(
                self.articles_with_subcat.items(),
                key=lambda x: x[0].lower(),
            ))
            for subcat, articles in self.articles_with_subcat:
                articles.sort(key=lambda a: a.title.lower())
                n_articles += len(articles)
                list_article += f'\n<h3>{subcat}</h3>\n'
                list_article += Page.as_ul_of_links(
                    articles, self.path, with_ts=True,
                )

        context = {
            'category_name': self.cat_name,
            'n_articles': n_articles,
            'list_article': list_article,
        }
        context.update(CategoryPage.additional_context)
        super().generate_from_template(template, context)


class ArticlePage(Page):
    def collect_categories(self, soup, all_cats, all_cat_paths):
        elm_cats = soup.find(class_='categories')
        if elm_cats is not None:
            cats = elm_cats.find_all('a')
            for cat in cats:
                cat_name = cat.get_text()
                cat_path = (self.path.parent / Path(cat['href'])).resolve()
                if cat_name not in all_cats:
                    if cat_path in all_cat_paths:
                        self.raise_error(f'カテゴリ名のゆれ {cat_name}')
                    all_cats[cat_name] = CategoryPage(
                        cat_name, cat_path, self.subsite_name,
                    )
                    all_cat_paths.add(cat_path)
                elif cat_path != all_cats[cat_name].path:
                    self.raise_error(f'カテゴリページパスのゆれ {cat_path}')
                subcat = cat.get('data-subcat')
                if subcat is None:
                    all_cats[cat_name].articles.append(self)
                else:
                    if subcat not in all_cats[cat_name].articles_with_subcat:
                        all_cats[cat_name].articles_with_subcat[subcat] = []
                    all_cats[cat_name].articles_with_subcat[subcat].append(self)


class IndexPage(Page):
    additional_context = {}

    def collect_articles(self):
        # 記事ページ収集
        logger.info('記事ページ収集')
        articles = []
        all_cats = {}
        all_cat_paths = set()
        article_dir = self.path.parent / 'articles'
        for article_path in Path(article_dir).glob('*.html'):
            article = ArticlePage(article_path, self.subsite_name)
            soup = article.eval(return_soup=True)
            article.collect_categories(soup, all_cats, all_cat_paths)
            articles.append(article)
        return articles, list(all_cats.values()), all_cat_paths

    def generate_categories(self, cat_template_path, all_cat_paths):
        logger.info('カテゴリページ生成')
        cat_template = Template(cat_template_path.read_text(encoding='utf8'))
        for cat in self.all_cats:
            cat.generate_from_template(cat_template)

        # 廃れたカテゴリページがないことの確認
        cat_dir = self.path.parent / 'categories'
        for cat_path in Path(cat_dir).glob('*.html'):
            if cat_path not in all_cat_paths:
                raise ValueError(f'廃れたカテゴリページ {cat_path}')

    def __init__(
        self,
        subsite_root,
        subsite_template_root,
        subsite_name,
    ):
        index_template_path = subsite_template_root / 'index_template.html'
        cat_template_path = subsite_template_root / 'category_template.html'
        if not index_template_path.is_file():
            raise ValueError(f'テンプレートがありません {index_template_path}')

        super().__init__(subsite_root / 'index.html', subsite_name)
        self.articles, self.all_cats, all_cat_paths = self.collect_articles()

        # 「記事一覧」 (タイトル順ソート)
        self.articles.sort(key=lambda a: a.title.lower())
        list_article = Page.as_ul_of_links(self.articles, self.path, with_ts=True)

        # 「更新日が新しい記事」 (同一更新日はタイトル順に)
        self.articles.sort(key=lambda a: a.timestamp, reverse=True)
        list_article_recent = Page.as_ul_of_links(
            self.articles, self.path, with_ts=True, n_max=10,
        )

        # 無駄なサイトマップ更新を防ぐためタイトル順に戻しておく
        self.articles.sort(key=lambda a: a.title.lower())

        # カテゴリページ生成
        self.all_cats.sort(key=lambda c: c.cat_name.lower())
        if cat_template_path.is_file():
            self.generate_categories(cat_template_path, all_cat_paths)
        print(self.all_cats[0].path)
        list_category = Page.as_ul_of_links(self.all_cats, self.path)

        # 目次ページ自身の生成
        logger.info('目次ページ生成')
        template = Template(index_template_path.read_text(encoding='utf8'))
        context = {
            'n_article': len(self.articles),
            'list_article': list_article,
            'list_article_recent': list_article_recent,
            'n_category': len(self.all_cats),
            'list_category': list_category,
        }
        context.update(IndexPage.additional_context)
        self.generate_from_template(template, context)

    def get_pages(self):
        return [self] + self.articles + self.all_cats


class Sitemap(File):
    def __init__(self, pages):
        # サイトマップ生成
        logger.info('サイトマップ生成')
        sitemap_path = File.site_root / 'sitemap.xml'
        super().__init__(sitemap_path)
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '\n'.join([page.as_xml_url() for page in pages]),
            '</urlset>',
        ]
        self.write_text('\n'.join(lines) + '\n')


def find_disallowed(path, allowlist, raise_error=True):
    result = []
    for p in path.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(path).as_posix()
        ok = any(fnmatch.fnmatch(rel, pat) for pat in allowlist)
        if not ok:
            result.append(rel)
    if result and raise_error:
        raise ValueError(f'許可されていないファイルがあります {result}')
    return result


@contextmanager
def build_index(
    site_root,  # サイトファイル群ルート (ページ更新日とサイトマップの相対パス用)
    last_counts_path='',  # ページ文字数最終更新日管理ファイルのパス
    domain='',  # ドメイン https://hoge.com/ (サイトマップ用)
    force_keep_timestamp = False,  # タイムスタンプを保つ (メンテナンス用)
):
    """
    サイトのインデックスとサイトマップを生成するためのコンテクストを与えます
    """
    File.site_root = site_root
    File.domain = domain
    Page.force_keep_timestamp = force_keep_timestamp
    Page.load_last_counts(last_counts_path)  # ページ更新日をロード
    yield
    Page.dump_last_counts(last_counts_path)  # ページ更新日をダンプ
