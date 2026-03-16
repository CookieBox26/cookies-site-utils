from cookies_site_utils.article_helper import ArticleHelper
from pathlib import Path


def test_article_helper(tmp_path):
    conf_path = Path('.helper.toml')

    conf_path.write_text('''
    subsite_name = "hoge"

    [[job_groups]]
    paths = ["tests/docs/articles/fuga.html"]
    [[job_groups.jobs]]
    job_type = "SOUPIFY"

    [[job_groups]]
    paths = ["tests/docs/articles/fugaga.html"]
    [[job_groups.jobs]]
    job_type = "COPY_FROM"
    base_path = "tests/docs/articles/fuga.html"
    new_title = "ふがが"
    categories = { fugagafugaga = "ふががふがが" }
    '''.replace('    ', ''), newline='\n', encoding='utf8')
    ArticleHelper.run(conf_path)

    Path('tests/docs/articles/fugaga.html').unlink()
    conf_path.unlink()
