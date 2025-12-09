from shirotsubaki.element import Element as Elm
from jinja2 import Template
from bs4 import BeautifulSoup
from pathlib import Path
import os
import toml
from datetime import datetime
from contextlib import contextmanager
import importlib.resources
import re


def validate_and_collect_page_paths(path, files_allowed, subdirs_allowed, collect_page=True):
    """
    path 以下に無許可のファイルやサブディレクトリがないか確認しながら .html ファイルを収集します
    逆に allowed なファイルやサブディレクトリが確実に存在するかは確認しません
    コミット漏れは git status -s で防いでください
    """
    page_paths = []
    for child in path.iterdir():
        if child.is_dir() and child.name not in subdirs_allowed:
            raise ValueError(f'不要なサブディレクトリがある {child}')
        if child.is_file() and child.name not in files_allowed:
            if collect_page and child.suffix.lower() == '.html':
                page_paths.append(child)
            else:
                raise ValueError(f'不要なファイルがある {child}')
    return page_paths


def validate(path, files_allowed, subdirs_allowed):
    validate_and_collect_page_paths(path, files_allowed, subdirs_allowed, collect_page=False)


class File:
    site_root = None
    domain = None

    def __init__(self, path):
        self.path = path
        self.rel_path = Path(os.path.relpath(self.path, File.site_root)).as_posix()
        self.url = File.domain + self.rel_path

    def write_text(self, text):
        if self.path.exists():
            current_text = self.path.read_text(encoding='utf8')
            if current_text == text:
                print(f'更新なし {self.rel_path}')
                return
            print(f'更新あり {self.rel_path}')
        else:
            print(f'新規作成 {self.rel_path}')
        self.path.write_text(text, newline='\n', encoding='utf8')

    def load_style_css(self):
        resource_path = importlib.resources.files('cookies_site_utils') / 'resources/style.css'
        self.write_text(resource_path.read_text(encoding='utf-8'))

    def load_func_js(self):
        resource_path = importlib.resources.files('cookies_site_utils') / 'resources/funcs.js'
        self.write_text(resource_path.read_text(encoding='utf-8'))


class PageCharCounter:
    """
    ページの文字数をカウントします
    - インライン要素の閉じタグ直後の1つ以上の改行を1つの改行とみなします
    - ブロック要素の閉じタグ直後の1つ以上の改行を無視します
    """
    def __init__(self):
        self.closing_tag = re.compile(r'(</[^>]+>)\n+')
        self.inline_tags = {'span', 'a', 'code'}

    def _closing_tag_repl(self, match):
        tag = match.group(1)
        if tag[2:-1].strip() in self.inline_tags:
            return tag + '\n'
        return tag

    def normalize(self, text):
        return self.closing_tag.sub(self._closing_tag_repl, text)

    def __call__(self, text):
        return len(self.normalize(text))


class Page(File):
    last_counts = None
    force_keep_timestamp = False

    @classmethod
    def load_last_counts(cls, last_counts_path):
        with open(last_counts_path, encoding='utf8') as f:
            pages = toml.load(f)['pages']
            cls.last_counts = {page['rel_path']: page for page in pages}

    @classmethod
    def dump_last_counts(cls, last_counts_path):
        with open(last_counts_path, mode='w', encoding='utf8', newline='\n') as f:
            toml.dump({'pages': [v[1] for v in sorted(cls.last_counts.items())]}, f)

    def get_file_timestamp(self):
        return datetime.fromtimestamp(self.path.stat().st_mtime).strftime('%Y-%m-%d')

    def eval(self, subsite_name=None):
        text = self.path.read_text(encoding='utf8')
        soup = BeautifulSoup(text, 'html.parser')

        self.title = soup.find('h1').get_text()
        page_title = soup.title.get_text()
        if subsite_name is None:
            pass
        elif self.is_index:
            if page_title != f'{subsite_name}':
                raise ValueError(f'title タグがサブサイト名でない {self.path}')
        else:
            if page_title != f'{self.title} - {subsite_name}':
                raise ValueError(f'title タグが h1 タグ + サブサイト名でない {self.path}')

        for tag in soup.find_all(True):
            if tag.has_attr('style'):
                raise ValueError(f'インラインスタイルがある {self.path}')

        for a in soup.find_all('a'):
            if a.has_attr('target'):
                raise ValueError(f'a タグに target 属性がある {self.path}')

        links = soup.find_all('link', {'rel': 'stylesheet'})
        for link in links:
            css = link['href']
            if css.startswith('http'):
                continue
            # print(css)

        count = self.counter(text)
        last_count = 0
        if self.rel_path in Page.last_counts:
            last_count = Page.last_counts[self.rel_path]['count']
        else:
            Page.last_counts[self.rel_path] = {'rel_path': self.rel_path}

        if not Page.force_keep_timestamp:
            if count == last_count:  # 文字数が前回と一致していれば前回登録時のタイムスタンプを取る
                self.timestamp = Page.last_counts[self.rel_path]['timestamp']
            else:  # 文字数が前回と不一致であればファイルタイムスタンプを取る
                self.timestamp = self.get_file_timestamp()
                Page.last_counts[self.rel_path]['timestamp'] = self.timestamp  # タイムスタンプ登録
                Page.last_counts[self.rel_path]['count'] = count  # 文字数登録
        else:  # タイムスタンプを保つモード (メンテナンス用)
            # 前回のタイムスタンプがあれば取りなければファイルタイムスタンプを取る
            self.timestamp = Page.last_counts[self.rel_path].get('timestamp', None)
            if self.timestamp is None:
                self.timestamp = self.get_file_timestamp()
                Page.last_counts[self.rel_path]['timestamp'] = self.timestamp  # タイムスタンプ登録
            Page.last_counts[self.rel_path]['count'] = count  # 文字数登録

        print(self.timestamp, self.title, f'({last_count} --> {count})')
        return soup

    def __init__(self, path):
        super().__init__(path)
        self.is_index = (type(self).__name__ == 'IndexPage')
        self.counter = PageCharCounter()

    def generate(self, template, context, subsite_name):
        rendered = template.render(context) + '\n'
        self.write_text(rendered)
        self.eval(subsite_name)

    def as_anchor(self, source_path, with_ts=False):
        rel_path_from_source = Path(os.path.relpath(self.path, source_path.parent)).as_posix()
        elm_a = str(Elm('a', self.title).set_attr('href', rel_path_from_source)).replace('\n', '')
        if not with_ts:
            return elm_a
        elm_ts = str(Elm('span', self.timestamp).set_attr('class', 'index-ts')).replace('\n', '')
        return f'{elm_a} {elm_ts}'

    def as_xml_url(self):
        priority = 1.0 if self.is_index else 0.5
        lines = [
            '<url>',
            f'<loc>{self.url}</loc>',
            f'<lastmod>{self.timestamp}</lastmod>',
            '<changefreq>monthly</changefreq>',
            f'<priority>{priority}</priority>',
            '</url>',
        ]
        return '\n'.join(lines)

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

    def __init__(self, cat_name, path):
        super().__init__(path)
        self.cat_name = cat_name
        self.articles = []

    def generate(self, template, subsite_name):
        self.articles.sort(key=lambda a: a.title)
        context = {
            'category_name': self.cat_name,
            'n_articles': len(self.articles),
            'list_article': Page.as_ul_of_links(self.articles, self.path, with_ts=True),
        }
        context.update(CategoryPage.additional_context)
        super().generate(template, context, subsite_name)


class ArticlePage(Page):
    def __init__(self, path, all_cats, all_cat_paths, subsite_name):
        super().__init__(path)
        soup = self.eval(subsite_name)
        elm_cats = soup.find(class_='categories')
        if elm_cats is not None:
            cats = elm_cats.find_all('a')
            for cat in cats:
                cat_name = cat.get_text()
                cat_path = (path.parent / Path(cat['href'])).resolve()
                if cat_name not in all_cats:
                    if cat_path in all_cat_paths:
                        raise ValueError(f'カテゴリ名のゆれ {path}')
                    all_cats[cat_name] = CategoryPage(cat_name, cat_path)
                    all_cat_paths.add(cat_path)
                elif cat_path != all_cats[cat_name].path:
                    raise ValueError(f'カテゴリページパスのゆれ {path}')
                all_cats[cat_name].articles.append(self)


class IndexPage(Page):
    additional_context = {}

    def __init__(self, subsite_root):
        super().__init__(subsite_root / 'index.html')

    def build(self, subsite_template_root, subsite_name):
        all_cats = {}
        all_cat_paths = set()

        # 記事ページ収集
        print('[INFO] 記事ページ収集')
        self.articles = []
        article_dir = self.path.parent / 'articles'
        for article_path in validate_and_collect_page_paths(article_dir, [], []):
            article = ArticlePage(article_path, all_cats, all_cat_paths, subsite_name)
            self.articles.append(article)
        self.articles.sort(key=lambda a: a.title)  # 先にタイトル順ソート
        list_article = Page.as_ul_of_links(self.articles, self.path, with_ts=True)
        self.articles.sort(key=lambda a: a.timestamp, reverse=True)  # 同一更新日はタイトル順に
        list_article_recent = Page.as_ul_of_links(self.articles, self.path, with_ts=True, n_max=10)
        self.articles.sort(key=lambda a: a.title)  # 無駄なサイトマップ更新を防ぐため再度タイトル順

        # カテゴリページ生成
        print('[INFO] カテゴリページ生成')
        self.all_cats = list(all_cats.values())
        self.all_cats.sort(key=lambda c: c.cat_name)
        cat_template_path = subsite_template_root / 'category_template.html'
        cat_template = Template(cat_template_path.read_text(encoding='utf8'))
        for cat in self.all_cats:
            cat.generate(cat_template, subsite_name)
        list_category = Page.as_ul_of_links(self.all_cats, self.path)

        # 廃れたカテゴリページがないことの確認
        cat_dir = self.path.parent / 'categories'
        for cat_path in validate_and_collect_page_paths(cat_dir, [], []):
            if cat_path not in all_cat_paths:
                raise ValueError(f'廃れたカテゴリページ {cat_path}')

        # 目次ページ自身の生成
        print('[INFO] 目次ページ生成')
        template_path = subsite_template_root / 'index_template.html'
        template = Template(template_path.read_text(encoding='utf8'))
        context = {
            'n_article': len(self.articles),
            'list_article': list_article,
            'list_article_recent': list_article_recent,
            'n_category': len(self.all_cats),
            'list_category': list_category,
        }
        context.update(IndexPage.additional_context)
        self.generate(template, context, subsite_name)

    def get_pages(self):
        return [self] + self.articles + self.all_cats


class Sitemap(File):
    def __init__(self, pages):
        # サイトマップ生成
        print('[INFO] サイトマップ生成')
        sitemap_path = File.site_root / 'sitemap.xml'
        super().__init__(sitemap_path)
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '\n'.join([page.as_xml_url() for page in pages]),
            '</urlset>',
        ]
        self.write_text('\n'.join(lines) + '\n')


@contextmanager
def index_generation(
    site_root,  # サイトのファイル群のルート (相対パスをページ更新日管理とサイトマップとログに利用)
    style_css,  # style.css のパス (便利ツール側リソースを強制的に同期)
    funcs_js,  # funcs.js のパス (便利ツール側リソースを強制的に同期)
    last_counts_path,  # ページ文字数最終更新日の管理ファイルのパス
    domain='',  # ドメイン https://hoge.com/ (サイトマップ用) (サイトマップ生成しない場合は不要)
    force_keep_timestamp = False,  # ページ文字数が変わってもタイムスタンプを保つ (メンテナンス用)
):
    """サイトのインデックスページとサイトマップを生成するためのコンテクストを与えます
    """
    Page.force_keep_timestamp = force_keep_timestamp

    # サイト内のすべてのファイルで利用するパラメータをセット
    File.site_root = site_root
    File.domain = domain
    # style.css と funcs.js は便利ツール側リソースを強制的に同期
    File(style_css).load_style_css()
    File(funcs_js).load_func_js()

    Page.load_last_counts(last_counts_path)  # ページ文字数最終更新日をロード
    yield
    Page.dump_last_counts(last_counts_path)  # ページ文字数最終更新日をダンプ
