# cookies-site-utils

この便利ツールは、私の Web サイト群で共通に利用するリソースや機能 (以下) を管理しています。

- CSS
- JavaScript
- 目次ビルド機能
- 記事編集補助機能

Web サイト側リポジトリは以下のような構成を想定しています。特に ★ と ☆ 以下のファイル及びディレクトリはこの通りである必要があります。
```
www/  # ドメインルート
  ├ sitemap.xml  # 必要であれば
  ├ funcs.js
  ├ css/*.css
  ├ site_0/  # サイト0 (目次ビルド対象サイト) ★
  │  ├ index.html
  │  ├ articles/*.html
  │  └ categories/*.html
  ├ site_1/

templates/  # テンプレート置き場
  ├ site_0/  # サイト0 (目次ビルド対象サイト) のテンプレート ☆
  │  ├ index_template.html
  │  └ category_template.html

.last_counts.toml  # ページ文字数最終更新日管理ファイル
build.py
```

## 利用方法

ローカル環境ではこの便利ツールをエディタブルモードでインストールしておくと便利です。必要に応じてこちらの便利ツールも修正しながら開発できます。
```
pip install -e .
```
もしこの便利ツールを修正した場合は、

1. Web サイト側のプッシュより先に、便利ツールの修正をプッシュしてください。
2. Web サイト側のビルドスクリプト内インラインメタデータにあるこの便利ツールのコミットハッシュを、修正済みのコミットハッシュに更新ください (さもないと修正が自動ビルドに反映されません)。
    - `python sync_hash.py` で自動更新できます。

## 各機能の説明

### CSS
`cookies_site_utils.get_style_css(pathlib.Path('site/css/style.css'))` のようにロードできます。

### JavaScript
`cookies_site_utils.get_funcs_js(pathlib.Path('site/funcs/js'))` のようにロードできます。

### 目次ビルド機能
記事ページ群からカテゴリページ群と目次ページを自動生成します。使用例は以下を参照ください。  

- https://github.com/CookieBox26/cookie-box/blob/main/build.py

### 記事編集補助機能

既存記事をベースに新規記事を作成したり、記事に参考文献を追加したり、リソースへのリンクでクエリするタイムスタンプを更新できます。実行したいジョブを TOML ファイルに設定してコマンド `ah` を実行してください。

- デフォルトで `.helper.toml` を読み込みます。TOML ファイルパスが異なるときは引数に渡してください。
- 実行できるジョブ種別は以下です。
    - `COPY_FROM`： 既存記事をベースに記事を新規作成します (既に記事が存在する場合はエラー)。
    - `ADD_REFERENCE`： 記事に参考文献を追加します。
    - `UPDATE_QUERY_TIMESTAMP`： リソースへのリンクでクエリするタイムスタンプを更新します。
- TOML ファイルに設定する変数は以下です。
    - `site_name`： サイト名。`COPY_FROM` でのみページタイトルで使います。
    - `templates`： テンプレートのデプロイ先ディレクトリ。`UPDATE_QUERY_TIMESTAMP` でのみリソースへの相対パスを取得するために使います。
    - `text_editor`, `web_browser`： 指定した場合は最後に編集した記事をエディタとブラウザで開きます。
    - `job_groups.paths`： このジョブ群を適用するパスのリスト。ワイルドカードも使用できます。
    - `job_groups.jobs.job_type`： ジョブ種別の指定。これに加えジョブ種別に応じた引数も必要です。
    - `job_groups.skip`： `skip = true` でこのジョブ群をスキップします (コメントアウト的に利用ください)。

#### ジョブ設定例. 既存記事をベースに新規記事を作成して参考文献も追加
```toml
text_editor = "C:\\Program Files (x86)\\sakura\\sakura.exe"
web_browser = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
site_name = "Cookie Box"

[[job_groups]]
paths = ["site/ja/articles/jupyter-notebook-convert-to-pdf.html"]
[[job_groups.jobs]]
job_type = "COPY_FROM"
base_path = "site/ja/articles/pandas-styler.html"
new_title = "Jupyter Notebook を PDF に変換する方法"
categories = { jupyter-notebook = "Jupyter Notebook" }
[[job_groups.jobs]]
job_type = "ADD_REFERENCE"
[[job_groups.jobs.references]]
url = "https://nbconvert.readthedocs.io/en/latest/usage.html"
title = "Using as a command line tool &#8212; nbconvert 7.16.6 documentation"
```

#### ジョブ設定例. リソースへのリンクでクエリするタイムスタンプを更新
```toml
[templates]
"templates/ja/index_template.html" = "site/ja/"
"templates/ja/category_template.html" = "site/ja/categories/"

[[job_groups]]
paths = [
  "site/ja/articles/*.html",
  "templates/ja/category_template.html",
  "templates/ja/index_template.html",
]
jobs = [
  { job_type = "UPDATE_QUERY_TIMESTAMP", resource = "site/css/style.css", timestamp = "2025-10-18" },
  { job_type = "UPDATE_QUERY_TIMESTAMP", resource = "site/css/cookie-box.css", timestamp = "2025-10-18" },
  { job_type = "UPDATE_QUERY_TIMESTAMP", resource = "site/funcs.js", timestamp = "2025-10-18" },
]
```
