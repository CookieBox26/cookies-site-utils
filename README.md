# cookies-site-utils

この便利ツールは、私の Web サイト群で利用するリソースや機能 (以下) を管理しています。

- リソース (JavaScript, CSS)
- 目次ビルド機能
- 記事編集補助機能

Web サイト側リポジトリは以下のような構成を想定しています。  
★ のファイルは必ず用意してください。  
☆ のファイルは必要に応じて用意してください。  
```
# 例1. シンプルな構成
~/
├─ docs/  # サイトルート (ディレクトリ名は任意)
│  ├─ sitemap.xml  # 必要ならサイトマップを生成可能
│  ├─ index.html  # テンプレートから生成
│  ├─ categories/*.html  # 必要ならテンプレートから生成
│  └─ articles/*.html  # ★
└─ templates/  # テンプレート置き場 (パスは任意)
    ├─ index_template.html  # ★
    └─ category_template.html  # ☆
```

```
# 例2. サブサイトが複数ある構成 (これもサイトマップを生成可能)
~/
├─ docs/  # サイトルート (ディレクトリ名は任意)
│  ├─ sitemap.xml  # 必要ならサイトマップを生成可能
│  ├─ subsite_0/  # サブサイトルート (ディレクトリ名は任意)
│  │    ├─ index.html  # テンプレートから生成
│  │    ├─ categories/*.html  # 必要ならテンプレートから生成
│  │    └─ articles/*.html  # ★
│  └─ subsite_1/  # サブサイトルート (ディレクトリ名は任意)
│        ├─ index.html  # テンプレートから生成
│        ├─ categories/*.html  # 必要ならテンプレートから生成
│        └─ articles/*.html  # ★
└─ templates/
    ├─ subsite_0/  # サブサイトのテンプレート置き場 (パスは任意)
    │    ├─ index_template.html  # ★
    │    └─ category_template.html  # ☆
    └─ subsite_1/  # サブサイトのテンプレート置き場 (パスは任意)
          ├─ index_template.html  # ★
          └─ category_template.html  # ☆
```


## 利用方法
ローカル環境ではこの便利ツールをエディタブルモードでインストールしておくと便利です。  
必要に応じてこちらの便利ツールも修正しながら開発できます。  
```
pip install -e .
```
もしこの便利ツールを修正した場合は、

1. Web サイト側より先にこの便利ツールの修正をプッシュしてください。
2. Web サイト側のビルドスクリプト `build.py` 内インラインメタデータにあるこの便利ツールのコミットハッシュを、プッシュしたコミットハッシュに更新ください。Web サイト側ルートで `csu s` を実行することで自動更新できます。

### 最新のリソース取得と目次ビルド機能
以下のような `build.py` で最新のリソース (JavaScript, CSS) 取得、目次ビルド、意図しないファイルがないかの確認ができます。
```py
# /// script
# requires-python = "==3.11.*"
# dependencies = [
#     "cookies_site_utils",
# ]
# [tool.uv.sources.cookies_site_utils]
# git = "https://github.com/CookieBox26/cookies-site-utils"
# rev = "1e2db74afb9eb3402646dab686cd1d3b5c9a3801"
# ///
from cookies_site_utils.resources import sync_resource
from cookies_site_utils.builder import find_disallowed, build_index, IndexPage
from pathlib import Path


if __name__ == '__main__':
    work_root = Path(__file__).resolve().parent
    site_root = work_root / 'docs'
    sync_resource(site_root / 'css/style.css')
    sync_resource(site_root / 'funcs.js')

    with build_index(
        site_root,
        last_counts_path=(work_root / '.last_counts.toml'),
        force_keep_timestamp=False,
    ):
        _ = IndexPage(
            site_root,
            work_root / 'templates',
            'Cookipedia α-version',
        )

    find_disallowed(site_root, allowlist=[
        'funcs.js',
        'css/*.css',
        'index.html',
        'categories/*.html',
        'articles/*.html',
        'utils/*.html',
    ])
```

### 記事編集補助機能

既存記事をベースに新規記事を作成したり、記事に参考文献を追加したり、リソースへのリンクでクエリするタイムスタンプを更新できます。実行したいジョブを TOML ファイルに設定してコマンド `csu a` を実行してください。

- デフォルトで `.helper.toml` を読み込みます。TOML ファイルパスが異なるときは引数に追加で渡してください。
- 実行できるジョブ種別は以下です。
    - `COPY_FROM`： 既存記事をベースに記事を新規作成します (既に記事が存在する場合はエラー)。
    - `ADD_REFERENCES`： 記事に参考文献を追加します。
    - `UPDATE_TIMESTAMP`： リソースへのリンクでクエリするタイムスタンプを更新します。
    - `SOUPIFY`： 記事の整形のみ行います。
- TOML ファイルに設定する変数は以下です。
    - `subsite_name`： サブサイト名。`COPY_FROM` でのみページタイトルで使います。
    - `templates`： テンプレートのデプロイ先ディレクトリ。`UPDATE_QUERY_TIMESTAMP` でのみリソースへの相対パスを取得するために使います。
    - `text_editor`, `web_browser`： 指定した場合は最後に編集した記事をエディタとブラウザで開きます。
    - `job_groups.skip`： `skip = true` でこのジョブ群をスキップします (コメントアウト的に利用ください)。
    - `job_groups.paths`： このジョブ群を適用するパスのリスト。ワイルドカードも使用できます。
    - `job_groups.jobs.job_type`： ジョブ種別の指定。これに加えジョブ種別に応じた引数も必要です。

#### ジョブ設定例
```toml
text_editor = "C:\\Program Files (x86)\\sakura\\sakura.exe"
web_browser = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
subsite_name = "Cookipedia α-version"
[templates]
"templates/index_template.html" = "docs/"
"templates/category_template.html" = "docs/categories/"


# ========== 記事の新規作成 ==========
[[job_groups]]
paths = ["docs/articles/stylus.html"]

[[job_groups.jobs]]
skip = false
job_type = "COPY_FROM"
base_path = "docs/articles/notepad-plus-plus.html"
new_title = "Stylus (ブラウザ拡張機能)"
categories = { }  # { jupyter-notebook = "Jupyter Notebook" }

[[job_groups.jobs]]
skip = true
job_type = "ADD_REFERENCES"
[[job_groups.jobs.references]]
url = "https://nbconvert.readthedocs.io/en/latest/usage.html"
title = "Using as a command line tool &#8212; nbconvert 7.16.6 documentation"

[[job_groups.jobs]]
job_type = "SOUPIFY"


# ========== タイムスタンプ更新 ==========
[[job_groups]]
skip = true
paths = [
  "templates/index_template.html",
  "templates/category_template.html",
  "docs/articles/*.html",
]
jobs = [
  { job_type = "UPDATE_TIMESTAMP", resource = "docs/css/style.css", timestamp = "2026-01-30" },
  { job_type = "UPDATE_TIMESTAMP", resource = "docs/css/cookipedia.css", timestamp = "2025-12-09" },
  { job_type = "UPDATE_TIMESTAMP", resource = "docs/funcs.js", timestamp = "2025-12-14" },
]
```
