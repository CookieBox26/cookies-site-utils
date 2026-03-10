from bs4 import BeautifulSoup, Doctype, Tag, Comment
from pathlib import Path
import os
import toml
import datetime
import subprocess
import argparse


class ArticleHelper:
    site_name = None
    templates = {}

    @classmethod
    def eq(cls, element, element_class_selector):
        tag, clazz = element_class_selector.split('.')
        return element.name == tag and clazz in element.get('class', [])

    @classmethod
    def _clear_children(cls, element, replace_to=''):
        for child in element.children:
            child.replace_with(replace_to)

    @classmethod
    def start_tag(cls, node):
        s = '<' + node.name
        for k, v in node.attrs.items():
            if isinstance(v, list):
                v = ' '.join(v)
            s += f' {k}="{v}"'
        return s + '>'

    @classmethod
    def target(cls, child):
        if child.name == 'div' and 'container' in child.get('class', []):
            return True
        if child.name == 'main' and 'main' in child.get('class', []):
            return True
        if child.name == 'div' and 'item' in child.get('class', []):
            return True
        return False

    @classmethod
    def decode(cls, node):
        decoded = ArticleHelper.start_tag(node)
        for child in node.children:
            if isinstance(child, Tag):
                if ArticleHelper.target(child):
                    decoded += ArticleHelper.decode(child)
                else:
                    if (child.name in ['h2', 'h3']) and (not decoded.endswith('\n\n')):
                        decoded += '\n'
                    decoded += child.decode()
            elif isinstance(child, Comment):
                decoded += f'<!--{child}-->'
            else:
                decoded += str(child)
        if node.name == 'div' and 'item' in node.get('class', []):
            decoded += '\n'
        decoded += f'</{node.name}>'
        return decoded

    def decode_soup(self):
        decoded = ''
        for node in self.soup.contents:
            if isinstance(node, Doctype):
                decoded += f'<!DOCTYPE {node}>\n\n'
            elif node.name == 'html':
                decoded += '<html>\n'
                decoded += self.soup.head.decode() + '\n'
                decoded += ArticleHelper.decode(self.soup.body) + '\n'
                decoded += '</html>\n'
        return decoded

    def generate(self):
        if self.soup is None:
            print('スープがないので何もしません')
        else:
            self.path.write_text(self.decode_soup(), encoding='utf8', newline='\n')
        print(self.path.as_posix())

    def __init__(self, path):
        self.path = path
        self.soup = None

    def set_soup(self):
        if self.soup is None:
            self.soup = BeautifulSoup(self.path.read_text(encoding='utf8'), 'html.parser')

    def soupify(self):
        self.set_soup()

    def copy_from(self, base_path, new_title, categories):
        if self.path.exists():
            raise ValueError(f'{self.path} exists.')
        self.soup = BeautifulSoup(Path(base_path).read_text(encoding='utf8'), 'html.parser')
        self.soup.title.string = f'{new_title} - {ArticleHelper.site_name}'
        self.soup.find('h1').string = new_title
        item = self.soup.select_one('div.item')
        cleared_last = False
        for child in item.children:
             clear = False
             if child.name == 'h1':
                 pass
             elif ArticleHelper.eq(child, 'div.categories'):
                 ArticleHelper._clear_children(child)
                 for i_cat, (cat_path, cat_name) in enumerate(categories.items()):
                     if i_cat != 0:
                         child.append(', ')
                     a_tag = self.soup.new_tag('a', href=f'../categories/{cat_path}.html')
                     a_tag.string = cat_name
                     child.append(a_tag)
             elif ArticleHelper.eq(child, 'div.summary'):
                 ul_tag = child.select_one('ul')
                 ArticleHelper._clear_children(ul_tag)
                 ul_tag.extend(['\n', self.soup.new_tag('li'), '\n'])
             elif child.name == 'h2' and child.string == '参考文献':
                 pass
             elif ArticleHelper.eq(child, 'ol.ref'):
                 ArticleHelper._clear_children(child)
             else:
                 clear = True
             if clear:
                 child.replace_with('' if cleared_last else '\n')
                 cleared_last = True
             else:
                 cleared_last = False

    def update_timestamp(self, resource, timestamp):
        self.set_soup()
        parent = self.path.resolve().parent
        if self.path in ArticleHelper.templates:
            parent = ArticleHelper.templates[self.path]
        rel_path = Path(os.path.relpath(Path(resource).resolve(), parent)).as_posix()

        if rel_path.endswith('.css'):
            links = self.soup.find_all('link', {'rel': 'stylesheet'})
            for link in links:
                if link['href'].startswith(rel_path):
                    link['href'] = f'{rel_path}?v={timestamp}'
        if rel_path.endswith('.js'):
            links = self.soup.find_all('script')
            for link in links:
                if not link.has_attr('src'):
                    continue
                if link['src'].startswith(rel_path):
                    link['src'] = f'{rel_path}?v={timestamp}'

    def add_reference(self, references):
        self.set_soup()
        today = datetime.datetime.now().strftime('%Y年%#m月%#d日')
        ol_tag = self.soup.select_one('ol.ref')
        for ref in references:
            li_tag = self.soup.new_tag('li')
            a_tag = self.soup.new_tag('a', href=ref['url'])
            a_tag['class'] = 'asis'
            li_tag.append(BeautifulSoup(ref['title'], 'html.parser'))
            li_tag.extend([', ', a_tag, f', {today}参照.'])
            ol_tag.append(li_tag)

    @classmethod
    def run_jobs(cls, path, jobs):
        processed = False
        ah = cls(path)
        for job in jobs:
            if job.get('skip', False):
                continue
            print('-', job['job_type'])
            if job['job_type'] == 'SOUPIFY':
                ah.soupify()
            if job['job_type'] == 'COPY_FROM':
                ah.copy_from(
                    base_path=job['base_path'],
                    new_title=job['new_title'],
                    categories=job['categories'],
                )
            if job['job_type'] == 'UPDATE_TIMESTAMP':
                ah.update_timestamp(job['resource'], job['timestamp'])
            if job['job_type'] == 'ADD_REFERENCE':
                ah.add_reference(job['references'])
            processed = True
        ah.generate()
        return processed, ah

    @classmethod
    def run(cls, conf_path):
        with open(conf_path, encoding='utf8') as f:
            conf = toml.load(f)
        if 'site_name' in conf:
            ArticleHelper.site_name = conf['site_name']
        if 'templates' in conf:
            for template, parent in conf['templates'].items():
                ArticleHelper.templates[Path(template)] = Path(parent).resolve()

        processed = False
        ah = None
        for job_group in conf['job_groups']:
            if job_group.get('skip', False):
                continue
            for path_raw in job_group['paths']:
                path = Path(path_raw)
                if '*' in path.name:
                    for path in path.parent.glob(path.name):
                        processed, ah = cls.run_jobs(path, job_group['jobs'])
                else:
                    processed, ah = cls.run_jobs(path, job_group['jobs'])

        if processed:
            if 'text_editor' in conf:
                subprocess.Popen([conf['text_editor'], ah.path.resolve()])
            if 'web_browser' in conf:
                subprocess.Popen([conf['web_browser'], ah.path.resolve()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('conf_path', type=str, nargs='?', default='.helper.toml')
    args = parser.parse_args()
    ArticleHelper.run(args.conf_path)


if __name__ == '__main__':
    main()
