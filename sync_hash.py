from pathlib import Path
import subprocess
import argparse
import re


def _run(command, cwd=None):
    ret = subprocess.run(
        command, capture_output=True, text=True, check=True, cwd=cwd,
    ).stdout.rstrip('\n')
    return ret


def sync_hash(target='../cookie-box/build.py', commit=False):
    """Web サイト側 build.py 内メタデータのコミットハッシュをこのツールの HEAD に同期させます

    Web サイト側 build.py 内に以下のような連続する行があることを期待します
    ```
    # git = "https://github.com/CookieBox26/cookies-site-utils"
    # rev = "f74b3fa4fbd36beff15b55e2ee2bd4928d06e0e5"
    ```
    """
    preceding = (
        '# git = "https://github.com/CookieBox26/cookies-site-utils"\n'
        '# rev = '
    )

    ret = _run(['git', 'log', '-1', '--pretty=oneline']).split()
    hash = ret[0]
    log = ' '.join(ret[1:])
    print(f'{hash}\n{log}')
    regexp = f'{preceding}"[a-z0-9]+"'
    latest = f'{preceding}"{hash}"'

    target_path = Path(target)
    text = target_path.read_text(encoding='utf8')
    if latest in text:
        print('Web サイト側 build.py は既にこのツールの HEAD を参照しているので終了します')
        return
    text = re.sub(regexp, latest, text)
    target_path.write_text(text, newline='\n', encoding='utf8')
    print('Web サイト側 build.py をこのツールの HEAD に同期しました')
    ret = _run(['git', 'status', '-s'], cwd=target_path.parent)
    if ret != ' M build.py':
        print('Web サイト側に他に未コミットの変更があるのでステージングせず終了します')
        return
    ret = _run(['git', 'diff', '--numstat'], cwd=target_path.parent)
    if ret != '1\t1\tbuild.py':
        print('Web サイト側 build.py に他の変更があるのでステージングせず終了します')
        return
    _run(['git', 'add', 'build.py'], cwd=target_path.parent)
    print('Web サイト側 build.py をステージングしました')
    if commit:
        print('Web サイト側 build.py をコミットします')
        ret = _run(['git', 'commit', '-m', log], cwd=target_path.parent)
        print(ret)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'targets', type=str, nargs='?',
        default='../cookie-box/build.py,../cookipedia/build.py',
    )
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    targets = args.targets.split(',')
    for target in targets:
        print('-' * 25 + '\n' + target + ' を更新します')
        sync_hash(target, args.commit)
