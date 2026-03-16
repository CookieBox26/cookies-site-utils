from bs4 import BeautifulSoup, Doctype, Tag, Comment, NavigableString
from pathlib import Path
import os
import datetime


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
                if child.name in ['ul', 'ol'] or _eq(child, 'div.categories'):
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
    ol_tag = item.find('ol', class_='ref')
    if ol_tag is None:
        h2_tag = item.find('h2', string='参考文献')
        if h2_tag is None:
            h2_tag = soup.new_tag('h2', string='参考文献')
            item.append(h2_tag)
            item.append('\n')
        ol_tag = soup.new_tag('ol', attrs={'class': 'ref'})
        item.append(ol_tag)
    today = datetime.datetime.now().strftime('%Y年%#m月%#d日')
    for ref in references:
        li_tag = soup.new_tag('li')
        a_tag = soup.new_tag('a', href=ref['url'])
        a_tag['class'] = 'asis'
        li_tag.append(BeautifulSoup(ref['title'], 'html.parser'))
        li_tag.extend([', ', a_tag, f', {today}参照.'])
        ol_tag.append(li_tag)
        ol_tag.append('\n')


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
    n = len(div_tag.find_all('a'))
    for cat_path, cat_name in cats.items():
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
         else:
             clear = True
         if clear:
             child.replace_with('' if cleared_last else '\n')
             cleared_last = True
         else:
             cleared_last = False
