import cookies_site_utils.soup_util as su
from bs4 import BeautifulSoup
import pytest


def test_start_tag():
    html = '<div class="item">Hello</div>'
    soup = BeautifulSoup(html, 'html.parser')
    node = soup.find('div', class_='item')
    s = su._start_tag(node)
    assert s == '<div class="item">'


def test_decode_soup():
    html = '''
    <!DOCTYPE HTML>
    <html>
    <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1" name="viewport"/>
    <title>あああ - hoge</title>
    <link href="../css/style.css?v=0" rel="stylesheet" type="text/css"/>
    <link href="../css/a.css?v=0" rel="stylesheet" type="text/css"/>
    <script data-repo="a" defer="true" id="app" src="../funcs.js?v=0"></script>
    </head>
    <body>
    <div class="container"><div id="sidebar"></div><main class="main">
    <div id="smartphone-header"></div><div class="item long-title"><h1>あああ</h1>
    あああああ。<div>いいい。</div><h2>参考文献</h2><ol class="ref">
    <li>あああ, <a class="asis" href="aaa"></a>, 2026年3月15日参照.</li></ol>
    <div class="categories">
    <a href="../categories/aaa.html">あああ</a> |
    <a href="../categories/iii.html">いいい</a>
    </div></div></main></div></body></html>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    decoded_1 = su.decode_soup(soup)
    # print(decoded_1)
    assert decoded_1.startswith('<!DOCTYPE HTML>\n\n')
    assert '>\n<h1>' in decoded_1
    assert decoded_1.endswith('\n\n</div>\n</main>\n</div>\n</body>\n</html>\n')
    decoded_2 = su.decode_soup(BeautifulSoup(decoded_1, 'html.parser'))
    assert decoded_2 == decoded_1


def test_update_timestamp():
    html = '''
    <link href="../css/style.css?v=0" rel="stylesheet" type="text/css"/>
    <link href="../css/a.css?v=0" rel="stylesheet" type="text/css"/>
    <script data-repo="a" defer="true" id="app" src="../funcs.js?v=0"></script>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.update_timestamp(soup, 'docs/articles', 'docs/css/style.css', '1')
    su.update_timestamp(soup, 'docs/articles', 'docs/css/a.css', '2')
    su.update_timestamp(soup, 'docs/articles', 'docs/funcs.js', '3')
    assert len(soup.find_all('link', {'href': '../css/style.css?v=1'})) == 1
    assert len(soup.find_all('link', {'href': '../css/a.css?v=2'})) == 1
    assert len(soup.find_all('script', {'src': '../funcs.js?v=3'})) == 1


def test_set_title():
    html = '''
    <title>あああ - hoge</title>
    <h1>あああ</h1>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.set_title(soup, 'いいい', 'hoge')
    assert soup.title.string == 'いいい - hoge'
    assert soup.find('h1').string == 'いいい'


def test_add_references():
    html = '''
    <div class="item">
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_references(soup, [
       {'title': 'あああ', 'url': 'aaa'},
    ])
    h2_tag = soup.find_all('h2', string='参考文献')
    assert len(h2_tag) == 1
    refs = soup.find('ol', class_='ref').find_all('li')
    assert len(refs) == 1

    html = '''
    <div class="item">
    <h2>参考文献</h2>
    <ol class="ref">
    <li>あああ, <a class="asis" href="aaa"></a>, 2026年3月15日参照.</li>
    </ol>
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_references(soup, [
       {'title': 'いいい', 'url': 'iii'},
       {'title': 'ううう', 'url': 'uuu'},
    ])
    h2_tag = soup.find_all('h2', string='参考文献')
    assert len(h2_tag) == 1
    refs = soup.find('ol', class_='ref').find_all('li')
    assert len(refs) == 3

    su.add_references(soup, [
       {'title': 'いいい', 'url': 'iii'},
       {'title': 'ううう', 'url': 'uuu'},
    ])
    h2_tag = soup.find_all('h2', string='参考文献')
    assert len(h2_tag) == 1
    refs = soup.find('ol', class_='ref').find_all('li')
    assert len(refs) == 3


def test_dd_signature():
    def make_dd(html):
        return BeautifulSoup(html, 'html.parser').find('dd')

    a_aaa = '<a href="aaa">タイトル</a>'
    a_bbb = '<a href="bbb">タイトル</a>'
    li_aaa = f'<li>{a_aaa}</li>'
    li_bbb = f'<li>{a_bbb}</li>'

    # テキストと URL が同じなら同一シグネチャ
    dd1 = make_dd(f'<dd>あああ<ul>{li_aaa}</ul></dd>')
    dd2 = make_dd(f'<dd>あああ<ul>{li_aaa}</ul></dd>')
    assert su._dd_signature(dd1) == su._dd_signature(dd2)

    # テキストが異なれば別シグネチャ
    dd3 = make_dd(f'<dd>いいい<ul>{li_aaa}</ul></dd>')
    assert su._dd_signature(dd1) != su._dd_signature(dd3)

    # URL が異なれば別シグネチャ
    dd4 = make_dd(f'<dd>あああ<ul>{li_bbb}</ul></dd>')
    assert su._dd_signature(dd1) != su._dd_signature(dd4)

    # URL なしの dd は links が空タプル
    dd5 = make_dd('<dd>あああ</dd>')
    assert su._dd_signature(dd5) == (('あああ',), ())

    # 複数 URL はすべてリンクに含まれる
    dd6 = make_dd(f'<dd>あああ<ul>{li_aaa}{li_bbb}</ul></dd>')
    dd7 = make_dd(f'<dd>あああ<ul>{li_aaa}{li_bbb}</ul></dd>')
    assert su._dd_signature(dd6) == su._dd_signature(dd7)
    dd8 = make_dd(f'<dd>あああ<ul>{li_aaa}</ul></dd>')
    assert su._dd_signature(dd6) != su._dd_signature(dd8)


def test_add_references_with_key(monkeypatch):
    html = '''
    <div class="item">
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_references_with_key(soup, [
       {'key': 'a', 'title': 'あああ', 'urls': ['aaa']},
    ])
    h2_tag = soup.find_all('h2', string='参考文献')
    assert len(h2_tag) == 1
    refs = soup.find('dl', class_='ref').find_all('dt')
    assert len(refs) == 1

    html = '''
    <div class="item">
    <h2>参考文献</h2>
    <dl class="ref">
    <dt>a</dt>
    <dd>あああ
    <ul>
    <li><a class="asis" href="aaa"></a></li>
    </ul>
    </dd>
    </dl>
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_references_with_key(soup, [
       {'key': 'i', 'title': 'いいい', 'urls': ['iii']},
       {'key': 'u', 'title': 'ううう', 'urls': ['uuu', 'uuuu']},
    ])
    refs = soup.find('dl', class_='ref').find_all('dt')
    assert len(refs) == 3

    # 同一内容なら input が呼ばれない (No updates)
    calls = []
    monkeypatch.setattr('builtins.input', lambda p: calls.append(p) or 'n')
    su.add_references_with_key(soup, [
       {'key': 'i', 'title': 'いいい', 'urls': ['iii']},
       {'key': 'u', 'title': 'ううう', 'urls': ['uuu', 'uuuu']},
    ])
    assert len(calls) == 0
    refs = soup.find('dl', class_='ref').find_all('dt')
    assert len(refs) == 3

    # 異なる内容なら input が呼ばれる (Already registered)
    calls = []
    monkeypatch.setattr('builtins.input', lambda p: calls.append(p) or 'n')
    su.add_references_with_key(soup, [
       {'key': 'i', 'title': 'いいいい', 'urls': ['iiii']},
    ])
    assert len(calls) == 1
    refs = soup.find('dl', class_='ref').find_all('dt')
    assert len(refs) == 3
    assert soup.find_all('a')[1]['href'] == 'iii'

    # 上書きを承認したら dd が更新される
    calls = []
    monkeypatch.setattr('builtins.input', lambda p: calls.append(p) or 'y')
    su.add_references_with_key(soup, [
       {'key': 'i', 'title': 'いいいい', 'urls': ['iiii']},
    ])
    assert len(calls) == 1
    refs = soup.find('dl', class_='ref').find_all('dt')
    assert len(refs) == 3
    assert soup.find_all('a')[1]['href'] == 'iiii'


def test_add_categories():
    html = '''
    <div class="item">
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_categories(soup, [
        {'path': 'aaa', 'name': 'あああ'},
        {'path': 'iii', 'name': 'いいい'},
    ])
    cats = soup.find('div', class_='categories').find_all('a')
    assert len(cats) == 2

    html = '''
    <div class="item">
    <div class="categories">
    <a href="../categories/aaa.html">あああ</a> |
    <a href="../categories/iii.html">いいい</a>
    </div>
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_categories(soup, [
        {'path': 'uuu', 'name': 'ううう'},
        {'path': 'eee', 'name': 'えええ'},
    ])
    cats = soup.find('div', class_='categories').find_all('a')
    assert len(cats) == 4

    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.add_categories(soup, [
        {'path': 'aaa', 'name': 'あああ'},
    ])
    cats = soup.find('div', class_='categories').find_all('a')
    assert len(cats) == 2

    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    with pytest.raises(ValueError):
        su.add_categories(soup, [
            {'path': 'aaa', 'name': 'ああああ'},
        ])


def test_clear_item():
    html = '''
    <div class="item">
    <h2>参考文献</h2>
    <ol class="ref">
    <li>あああ, <a class="asis" href="aaa"></a>, 2026年3月15日参照.</li>
    </ol>
    <div class="categories">
    <a href="../categories/aaa.html">あああ</a> |
    <a href="../categories/iii.html">いいい</a>
    </div>
    </div>
    '''
    soup = BeautifulSoup(html.replace('    ', ''), 'html.parser')
    su.clear_item(soup)
    h2_tag = soup.find_all('h2', string='参考文献')
    assert len(h2_tag) == 1
    refs = soup.find('ol', class_='ref').find_all('li')
    assert len(refs) == 0
    cats = soup.find('div', class_='categories').find_all('a')
    assert len(cats) == 0
