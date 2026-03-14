from cookies_site_utils.builder import build_index, IndexPage, validate
from pathlib import Path
# 以下は実際には pytest では効かないので pyproject.toml で指定している
import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
)


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
        validate(site_root, ['index.html'], ['articles'])
