from bs4 import BeautifulSoup, Doctype, Tag, Comment, NavigableString
from pathlib import Path
import os
import datetime
import logging
logger = logging.getLogger(__name__)


def _fmt(s):
    i = s.find('>')
    if i != -1 and (i + 1 >= len(s) or s[i+1] != '\n'):
        s = s[:i+1] + '\n' + s[i+1:]
    i = s.rfind('<')
    if i != -1 and (i == 0 or s[i-1] != '\n'):
        s = s[:i] + '\n' + s[i:]
    return s


def _start_tag(node):
    s = '<' + node.name
    for k, v in node.attrs.items():
        if isinstance(v, list):
            v = ' '.join(v)
        s += f' {k}="{v}"'
    return s + '>'


def _eq(element, element_class_selector):
    tag, clazz = element_class_selector.split('.')
    return element.name == tag and clazz in element.get('class', [])


def _decode(node):
    def _target(child):
        if child.name in ['head', 'body']:
            return True
        if _eq(child, 'div.container'):
            return True
        if _eq(child, 'main.main'):
            return True
        if _eq(child, 'div.item'):
            return True
        return False

    decoded = _start_tag(node)
    for child in node.children:
        if isinstance(child, Tag):
            if _target(child):
                decoded = decoded.rstrip('\n') + '\n'
                decoded += _fmt(_decode(child))
            else:
                if child.name in ['h2'] or _eq(child, 'div.categories'):
                    decoded = decoded.rstrip('\n') + '\n\n\n'
                elif child.name in ['h3']:
                    decoded = decoded.rstrip('\n') + '\n\n'
                elif child.name in ['h1', 'div', 'ul', 'ol']:
                    decoded = decoded.rstrip('\n') + '\n'
                _decoded = child.decode()
                if (
                    child.name in ['ul', 'ol', 'dl']
                    or _eq(child, 'div.categories')
                ):
                    _decoded = _fmt(_decoded)
                decoded += _decoded
        elif isinstance(child, Comment):
            decoded += f'<!--{child}-->'
        else:
            decoded += str(child)

    if _eq(node, 'div.item'):
        decoded = decoded.rstrip('\n') + '\n\n'
    else:
        decoded = decoded.rstrip('\n') + '\n'
    decoded += f'</{node.name}>'
    return decoded


def decode_soup(soup):
    decoded = ''
    for node in soup.contents:
        if isinstance(node, Doctype):
            decoded += f'<!DOCTYPE {node}>\n\n'
        elif node.name == 'html':
            decoded += _decode(node)
    return decoded + '\n'


def update_timestamp(soup, parent, resource, timestamp):
    if not isinstance(parent, Path):
        parent = Path(parent)
    rel_path = Path(os.path.relpath(Path(resource).resolve(), parent))
    rel_path = rel_path.as_posix()
    if rel_path.endswith('.css'):
        links = soup.find_all('link', {'rel': 'stylesheet'})
        for link in links:
            if link['href'].startswith(rel_path):
                link['href'] = f'{rel_path}?v={timestamp}'
    if rel_path.endswith('.js'):
        links = soup.find_all('script')
        for link in links:
            if not link.has_attr('src'):
                continue
            if link['src'].startswith(rel_path):
                link['src'] = f'{rel_path}?v={timestamp}'


def set_title(soup, title, subsite_name):
    if subsite_name is None:
        soup.title.string = title
    else:
        soup.title.string = f'{title} - {subsite_name}'
    soup.find('h1').string = title


def add_references(soup, references):
    item = soup.find('div', class_='item')
    dl_tag = item.find('dl', class_='ref')
    if dl_tag is not None:
        raise ValueError('There is a dl.ref')
    ol_tag = item.find('ol', class_='ref')
    if ol_tag is None:
        h2_tag = item.find('h2', string='参考文献')
        if h2_tag is None:
            h2_tag = soup.new_tag('h2', string='参考文献')
            item.append(h2_tag)
            item.append('\n')
        ol_tag = soup.new_tag('ol', attrs={'class': 'ref small'})
        item.append(ol_tag)

    today = datetime.datetime.now().strftime('%Y年%#m月%#d日')
    urls_existing = {a.get('href') for a in ol_tag.find_all('a')}
    for ref in references:
        if 'url' in ref and ref['url'] in urls_existing:
            logging.info(f'Already registered: url={ref["url"]}')
            continue
        li_tag = soup.new_tag('li')
        li_tag.append(BeautifulSoup(ref['title'], 'html.parser'))
        if 'url' in ref:
            a_tag = soup.new_tag('a', href=ref['url'])
            a_tag['class'] = 'asis'
            li_tag.extend([', ', a_tag, f', {today}参照.'])
        ol_tag.append(li_tag)
        ol_tag.append('\n')


def add_references_with_key(soup, references):
    item = soup.find('div', class_='item')
    ol_tag = item.find('ol', class_='ref')
    if ol_tag is not None:
        raise ValueError('There is a ol.ref')
    dl_tag = item.find('dl', class_='ref')
    if dl_tag is None:
        h2_tag = item.find('h2', string='参考文献')
        if h2_tag is None:
            h2_tag = soup.new_tag('h2', string='参考文献')
            item.append(h2_tag)
            item.append('\n')
        dl_tag = soup.new_tag('dl', attrs={'class': 'ref small'})
        item.append(dl_tag)

    today = datetime.datetime.now().strftime('%Y年%#m月%#d日')
    urls_existing = {a.get('href') for a in dl_tag.find_all('a')}
    for ref in references:
        if 'url' in ref and ref['url'] in urls_existing:
            logging.info(f'Already registered: url={ref["url"]}')
            continue
        dt_tag = soup.new_tag('dt')
        dt_tag.append(ref['key'])
        dd_tag = soup.new_tag('dd')
        dd_tag.append(BeautifulSoup(ref['title'], 'html.parser'))
        if 'url' in ref:
            a_tag = soup.new_tag('a', href=ref['url'])
            a_tag['class'] = 'asis'
            dd_tag.extend([', ', a_tag, f', {today}参照.'])
        dl_tag.append(dt_tag)
        dl_tag.append('\n')
        dl_tag.append(dd_tag)
        dl_tag.append('\n')


def add_categories(soup, cats):
    item = soup.find('div', class_='item')
    div_tag = item.find('div', class_='categories')
    if div_tag is None:
        div_tag = soup.new_tag('div', attrs={'class': 'categories'})
        item.append(div_tag)
    if (
        div_tag.contents
        and isinstance(div_tag.contents[-1], NavigableString)
    ):
        div_tag.contents[-1].extract()

    cats_old = {
        Path(a.get('href')).stem: a.get_text() for
        a in div_tag.find_all('a')
    }
    cat_names_old = {v: k for k, v in cats_old.items()}

    n = len(cats_old)
    for cat in cats:
        cat_path = cat['path']
        cat_name = cat['name']
        if cat_path in cats_old:
            if cat_name == cats_old[cat_path]:
                logging.info(
                    f'Already registered: path={cat_path}, name={cat_name}'
                )
                continue
            raise ValueError(
                f'Already registered with different name: '
                f'path={cat_path}, new={cat_name}, old={cats_old[cat_path]}'
            )
        elif cat_name in cat_names_old:
            raise ValueError(
                f'Already registered with different path: name={cat_name}, '
                f'new={cat_path}, old={cat_names_old[cat_name]}'
            )
        a_tag = soup.new_tag('a', href=f'../categories/{cat_path}.html')
        a_tag.string = cat_name
        if n != 0:
            div_tag.append(' |\n')
        div_tag.append(a_tag)


def _clear_children(element, replace_to=''):
    for child in element.children:
        child.replace_with(replace_to)


def clear_item(soup):
    item = soup.find('div', class_='item')
    cleared_last = False
    for child in item.children:
         clear = False
         if child.name == 'h1':
             pass
         elif _eq(child, 'div.categories'):
             _clear_children(child)
         elif _eq(child, 'div.summary'):
             ul_tag = child.select_one('ul')
             _clear_children(ul_tag)
             ul_tag.extend(['\n', soup.new_tag('li'), '\n'])
         elif child.name == 'h2' and child.string == '参考文献':
             pass
         elif _eq(child, 'ol.ref'):
             _clear_children(child)
         elif _eq(child, 'dl.ref'):
             _clear_children(child)
         else:
             clear = True
         if clear:
             child.replace_with('' if cleared_last else '\n')
             cleared_last = True
         else:
             cleared_last = False
