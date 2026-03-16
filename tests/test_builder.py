from cookies_site_utils.builder import (
    build_index, IndexPage, find_disallowed,
    ArticlePage,
)
from pathlib import Path


def test_build_index():
    work_root = Path(__file__).resolve().parent
    site_root = work_root / 'docs'
    last_counts_path = work_root / '.last_counts.toml'
    subsite_root = work_root / 'docs'
    subsite_template_root = work_root / 'templates'
    subsite_name = 'hoge'

    with build_index(site_root, last_counts_path=last_counts_path):
        index_ = IndexPage(
            subsite_root,
            subsite_template_root,
            subsite_name,
        )

    find_disallowed(site_root, allowlist=[
        'index.html',
        'categories/*.html',
        'articles/*.html',
    ])


def test_article_page():
    article = ArticlePage('tests/docs/articles/fuga.html', 'hoge')
    all_cats = {}
    all_cat_paths = set()
    soup = article.eval(return_soup=True)
    article.collect_categories(soup, all_cats, all_cat_paths)
    assert 'ふがふが' in all_cats
    assert all_cats['ふがふが'].cat_name == 'ふがふが'
