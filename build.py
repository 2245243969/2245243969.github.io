"""Build a dependency-free personal site. Python 3.10+; no pip install needed."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8-sig'))
ESC = html.escape


def local_path(target: str, prefix: str) -> str:
    """Keep local URLs usable both on GitHub Pages and when opening HTML files."""
    if target.startswith('/') and not target.startswith('//'):
        return prefix + target.lstrip('/')
    return target


def inline(value: str, prefix: str = '') -> str:
    tokens: list[str] = []

    def token(markup: str) -> str:
        tokens.append(markup)
        return f'\x00{len(tokens) - 1}\x00'

    value = re.sub(r'`([^`]+)`', lambda m: token('<code>' + ESC(m[1]) + '</code>'), value)

    def link(match: re.Match) -> str:
        image, label, target = match.groups()
        if not re.match(r'^(https?://|mailto:|/|#|\.?\.?/|[a-zA-Z0-9_-])', target) or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) and not target.startswith(('https://', 'http://', 'mailto:')):
            return ESC(label)
        url = ESC(local_path(target, prefix), quote=True)
        if image:
            return token(f'<img src="{url}" alt="{ESC(label, quote=True)}" loading="lazy">')
        return token(f'<a href="{url}">{ESC(label)}</a>')

    value = re.sub(r'(!?)\[([^\]]*)\]\(([^\s)]+)\)', link, value)
    value = ESC(value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', value)
    for i, markup in reversed(list(enumerate(tokens))):
        value = value.replace(f'\x00{i}\x00', markup)
    return value


def markdown(source: str, prefix: str) -> str:
    """Render the documented Markdown subset; source HTML is escaped."""
    result: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    code: list[str] | None = None

    def flush() -> None:
        if paragraph:
            result.append('<p>' + inline(' '.join(paragraph), prefix) + '</p>')
            paragraph.clear()

    def end_list() -> None:
        nonlocal list_type
        if list_type:
            result.append(f'</{list_type}>')
            list_type = None

    for line in source.splitlines():
        if line.startswith('```'):
            flush()
            end_list()
            if code is None:
                code = []
            else:
                result.append('<pre><code>' + ESC('\n'.join(code)) + '</code></pre>')
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        if not line.strip():
            flush()
            end_list()
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        item = re.match(r'^\s*(?:([-*])|\d+[.)])\s+(.+)$', line)
        if heading:
            flush()
            end_list()
            level = max(2, len(heading[1]))
            result.append(f'<h{level}>' + inline(heading[2], prefix) + f'</h{level}>')
        elif item:
            flush()
            kind = 'ul' if item[1] else 'ol'
            if list_type != kind:
                end_list()
                list_type = kind
                result.append(f'<{kind}>')
            result.append('<li>' + inline(item[2], prefix) + '</li>')
        elif line.startswith('> '):
            flush()
            end_list()
            result.append('<blockquote><p>' + inline(line[2:], prefix) + '</p></blockquote>')
        else:
            end_list()
            paragraph.append(line.strip())
    flush()
    end_list()
    if code is not None:
        result.append('<pre><code>' + ESC('\n'.join(code)) + '</code></pre>')
    return '\n'.join(result)


def load_posts() -> list[dict]:
    posts = []
    for source in sorted((ROOT / 'content/posts').glob('*.md')):
        if source.name.startswith('_'):
            continue
        text = source.read_text(encoding='utf-8-sig')
        parts = text.split('---', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f'{source.name}: missing front matter')
        meta = {}
        for line in parts[1].splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip().strip('\"\'')
        if meta.get('draft', 'false').lower() == 'true':
            continue
        for key in ('title', 'date', 'category'):
            if not meta.get(key):
                raise ValueError(f'{source.name}: missing {key}')
        dt.date.fromisoformat(meta['date'])
        if meta['category'] not in ('学习笔记', '生活随笔'):
            raise ValueError(f'{source.name}: category must be 学习笔记 or 生活随笔')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', source.stem):
            raise ValueError(f'{source.name}: use an English filename, such as my-first-post.md')
        posts.append({**meta, 'slug': source.stem, 'body': parts[2].strip()})
    return sorted(posts, key=lambda post: (post['date'], post['slug']), reverse=True)


def page(title: str, body: str, path: str, section: str, description: str | None = None) -> str:
    depth = len(Path(path).parts) - 1
    prefix = '../' * depth
    if path == '404.html':
        prefix = CONFIG['url'].rstrip('/') + '/'
    nav = []
    for label, target, key in [
        ('Home', 'index.html', 'home'),
        ('博客 · Blog', 'post/index.html', 'blog'),
        ('生活 · Life', 'life/index.html', 'life'),
    ]:
        current = ' aria-current="page"' if key == section else ''
        nav.append(f'<li><a href="{prefix}{target}"{current}><svg class="bookmark" viewBox="0 0 10 14" aria-hidden="true"><path d="M1 1h8v11l-4-3-4 3Z"/></svg><span class="nav-text">{label}</span></a></li>')
    name = ESC(CONFIG['name'])
    desc = ESC(CONFIG['description'])
    canonical = CONFIG['url'].rstrip('/') + '/' + ('' if path == 'index.html' else path.removesuffix('index.html'))
    document_title = name if section == 'home' else title + ' | ' + name
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{ESC(document_title)}</title>
  <meta name="description" content="{ESC(description or CONFIG['description'], quote=True)}">
  <meta name="theme-color" content="#fefefe">
  <meta property="og:title" content="{ESC(document_title, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:description" content="{ESC(description or CONFIG['description'], quote=True)}">
  <meta property="og:url" content="{ESC(canonical, quote=True)}">
  <link rel="canonical" href="{ESC(canonical, quote=True)}">
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{name}的博客" href="{prefix}feed.xml">
  <script src="{prefix}assets/theme.js"></script>
  <link rel="stylesheet" href="{prefix}assets/style.css">
  <script src="{prefix}assets/main.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">跳转到正文</a>
  <header class="sidebar">
    <div class="intro">
      <a class="avatar-link" href="{prefix}index.html" aria-label="{name}的首页"><img class="avatar" src="{prefix}{CONFIG['avatar']}" alt="{name}的照片" width="1706" height="1279"></a>
      <div><p class="sidebar-description">{name}，{desc}</p><a class="sidebar-github" href="{CONFIG['github']}">GitHub · 2245243969</a><a class="sidebar-email" href="mailto:{ESC(CONFIG['email'], quote=True)}">{ESC(CONFIG['email'])}</a></div>
    </div>
    <nav class="navigation" aria-label="主导航">
      <button class="menu-button" id="menu-button" aria-expanded="false" aria-controls="navigation-list">菜单 · Menu <span data-menu-state aria-hidden="true">+</span></button>
      <ul id="navigation-list">{''.join(nav)}</ul>
    </nav>
  </header>
  <div class="main-and-footer"><div class="page">
    <main id="main" tabindex="-1">{body}</main>
    <footer class="footer">
      <label class="theme-label" for="themer">dark theme: <input type="checkbox" id="themer" aria-label="深色主题"><span id="theme-state" aria-hidden="true">off</span></label>
      <p>{name} · <a href="{CONFIG['github']}">GitHub</a> · <a href="mailto:{ESC(CONFIG['email'], quote=True)}">QQ 邮箱</a> · <a href="{prefix}feed.xml">RSS</a></p>
      <p class="footer-note">个人主页 · 学习与生活</p>
    </footer>
  </div></div>
</body>
</html>
'''


def post_list(posts: list[dict], prefix: str) -> str:
    if not posts:
        return '<div class="empty"><p>还没有发布文章。</p><p>学习笔记与生活记录，陆续更新。</p></div>'
    rows = []
    for post in posts:
        rows.append(f'''<li><h2 class="post-title"><a href="{prefix}post/{post['slug']}/index.html">{ESC(post['title'])}</a></h2><p class="meta"><time datetime="{post['date']}">{post['date']}</time> · {ESC(post['category'])}</p><p>{ESC(post.get('summary', ''))}</p></li>''')
    return '<ul class="post-list">' + ''.join(rows) + '</ul>'


def build(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'assets').resolve() != (ROOT / 'assets').resolve():
        shutil.copytree(ROOT / 'assets', destination / 'assets', dirs_exist_ok=True)
    posts = load_posts()
    pages: dict[str, tuple[str, str, str]] = {}
    home = f'''<h1>{ESC(CONFIG['name'])}</h1>
<p class="bio">{ESC(CONFIG['description'])}</p>
<p>GitHub：<a href="{CONFIG['github']}">github.com/2245243969</a></p>
<p>QQ 邮箱：<a href="mailto:{ESC(CONFIG['email'], quote=True)}">{ESC(CONFIG['email'])}</a></p>
<h2>博客与生活：</h2>
{post_list(posts[:3], '') if posts else '<p class="muted">学习笔记与生活记录，陆续更新。</p>'}
<p class="section-link"><a href="post/index.html">浏览博客 →</a> &nbsp; <a href="life/index.html">生活记录 →</a></p>'''
    pages['index.html'] = (CONFIG['name'], home, 'home')
    blog_filters = [('全部', 'post/index.html'), ('学习笔记', 'post/study/index.html'), ('生活随笔', 'life/index.html')]
    for path, title, selected, category in [
        ('post/index.html', '博客', 'blog', None),
        ('post/study/index.html', '学习笔记', 'blog', '学习笔记'),
        ('life/index.html', '生活记录', 'life', '生活随笔'),
    ]:
        prefix = '../' * (len(Path(path).parts) - 1)
        links = ''.join(f'<li><a href="{prefix}{target}"' + (' aria-current="page"' if target == path else '') + f'>{label}</a></li>' for label, target in blog_filters)
        filtered = [post for post in posts if category is None or post['category'] == category]
        body = f'<h1>{title}</h1><p>学习笔记与生活记录。</p><ul class="filters" aria-label="文章分类">{links}</ul>' + post_list(filtered, prefix)
        pages[path] = (title, body, selected)
    for post in posts:
        section = 'life' if post['category'] == '生活随笔' else 'blog'
        parent = '../../life/index.html' if section == 'life' else '../index.html'
        body = f'<a class="back-link" href="{parent}">← 返回文章列表</a><article class="article"><h1>{ESC(post["title"])}</h1><p class="meta"><time datetime="{post["date"]}">{post["date"]}</time> · {ESC(post["category"])}</p>' + markdown(post['body'], '../../') + '</article>'
        pages[f'post/{post["slug"]}/index.html'] = (post['title'], body, section)
    pages['404.html'] = ('页面未找到', '<h1>页面未找到</h1><p>这个页面可能已经移动，或链接有误。</p><p><a href="' + CONFIG['url'] + '/">返回首页 →</a></p>', '')
    for path, (title, body, section) in pages.items():
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page(title, body, path, section), encoding='utf-8')
    (destination / '.nojekyll').touch()
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', CONFIG['name'] + '的博客'), ('link', CONFIG['url']), ('description', '学习笔记与生活记录'), ('language', 'zh-CN')]:
        ET.SubElement(channel, key).text = value
    for post in posts:
        item = ET.SubElement(channel, 'item')
        post_url = CONFIG['url'] + '/post/' + quote(post['slug']) + '/'
        for key, value in [('title', post['title']), ('link', post_url), ('guid', post_url), ('description', post.get('summary', ''))]:
            ET.SubElement(item, key).text = value
        date = dt.datetime.combine(dt.date.fromisoformat(post['date']), dt.time(), tzinfo=dt.timezone(dt.timedelta(hours=8)))
        ET.SubElement(item, 'pubDate').text = date.strftime('%a, %d %b %Y %H:%M:%S %z')
    ET.ElementTree(rss).write(destination / 'feed.xml', encoding='utf-8', xml_declaration=True)
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in pages:
        if path == '404.html':
            continue
        node = ET.SubElement(sitemap, 'url')
        ET.SubElement(node, 'loc').text = CONFIG['url'] + '/' + ('' if path == 'index.html' else path.removesuffix('index.html'))
    ET.ElementTree(sitemap).write(destination / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    (destination / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + CONFIG['url'] + '/sitemap.xml\n', encoding='utf-8')
    print(f'Built {len(pages)} pages; {len(posts)} published posts -> {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site', help='Output directory; default: _site')
    args = parser.parse_args()
    build((ROOT / args.output).resolve())
