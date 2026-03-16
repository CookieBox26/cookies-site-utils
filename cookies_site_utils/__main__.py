from cookies_site_utils.article_helper import ArticleHelper
from pathlib import Path
import subprocess
import argparse
import re


def _get_remote_head_hash():
    repo = 'https://github.com/CookieBox26/cookies-site-utils'
    command = f'git ls-remote {repo} HEAD | cut -f1'
    return subprocess.run(
        command.split(),
        capture_output=True,
        text=True,
    ).stdout.strip().split()[0]


def _sync_hash():
    """
    build.py 内メタデータで指定されているコミットハッシュを
    このツールのリモート HEAD にします
    build.py 内に以下のような連続する行があることを期待します
    ```
    # git = "https://github.com/CookieBox26/cookies-site-utils"
    # rev = "f74b3fa4fbd36beff15b55e2ee2bd4928d06e0e5"
    ```
    """
    hash = _get_remote_head_hash()
    target_path = Path('build.py')
    if not target_path.is_file():
        logging.warning(f'対象スクリプトがありません {target_path}')
        return
    preceding = (
        '# git = "https://github.com/CookieBox26/cookies-site-utils"\n'
        '# rev = '
    )
    regexp = f'{preceding}"[a-z0-9]+"'
    latest = f'{preceding}"{hash}"'
    text = target_path.read_text(encoding='utf8')
    if latest in text:
        logging.info('既に最新のコミットハッシュです')
        return
    text = re.sub(regexp, latest, text)
    target_path.write_text(text, newline='\n', encoding='utf8')
    logging.info('最新のコミットハッシュにしました')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('flag', choices=['s', 'a'])
    parser.add_argument(
        'article_helper_conf_path',
        nargs='?', type=str, default='.helper.toml',
    )
    args = parser.parse_args()

    if args.flag == 's':
        _sync_hash()
    elif args.flag == 'a':
        ArticleHelper.run(args.article_helper_conf_path)


if __name__ == '__main__':
    main()
