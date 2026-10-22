"""Build a dependency-free personal site. Python 3.10+; no pip install needed."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8-sig'))
ESC = html.escape
EN = {
    '主页': 'Home',
    '博客': 'Blog',
    '生活': 'Life',
    '生活记录': 'Life Notes',
    '论文精读': 'Paper Deep Dives',
    '概念理解': 'Concept Notes',
    '碎碎念': 'Random Thoughts',
    'QQ 邮箱': 'QQ Email',
    'B站主页': 'Bilibili',
    '浏览博客': 'Browse the Blog',
    '页面未找到': 'Page Not Found',
    '返回首页': 'Back to Home',
    '返回文章列表': 'Back to Articles',
}
BLOG_CATEGORIES = {
    '论文精读': 'post/study/index.html',
    '概念理解': 'post/concepts/index.html',
    '碎碎念': 'post/musings/index.html',
}


def bilingual(text: str) -> str:
    """Keep each interface label and its English translation together."""
    return ESC(text) + ' · <span lang="en">' + ESC(EN[text]) + '</span>'


def notes_intro() -> str:
    return '<p>论文精读、概念理解与碎碎念。</p><p class="translation" lang="en">Paper deep dives, concept notes, and random thoughts.</p>'


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
    value = re.sub(r'\$([^$\n]+)\$', lambda m: token('<span class="math-inline" data-tex="' + ESC(m[1], quote=True) + '">' + ESC(m[1]) + '</span>'), value)

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


def markdown(source: str, prefix: str, figures: dict | None = None) -> str:
    """Render the documented Markdown subset; source HTML is escaped."""
    result: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    code: list[str] | None = None
    math: list[str] | None = None

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
        if code is None and line.strip() == '$$':
            flush()
            end_list()
            if math is None:
                math = []
            else:
                tex = '\n'.join(math)
                result.append('<div class="math-display" data-tex="' + ESC(tex, quote=True) + '">' + ESC(tex) + '</div>')
                math = None
            continue
        if math is not None:
            math.append(line)
            continue
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
        figure = re.fullmatch(r'\{\{figure:([a-zA-Z0-9_-]+)\}\}', line.strip())
        if figure:
            flush()
            end_list()
            if not figures or figure[1] not in figures:
                raise ValueError('Unknown figure: ' + figure[1])
            result.append(paper_figure(figures[figure[1]], prefix))
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
    if math is not None:
        raise ValueError('Unclosed display math block')
    return '\n'.join(result)


def load_posts() -> list[dict]:
    posts = []
    sources = [(source, 'blog') for source in (ROOT / 'content/posts').glob('*.md')]
    sources += [(source, 'life') for source in (ROOT / 'content/life').glob('*.md')]
    for source, section in sorted(sources, key=lambda item: str(item[0])):
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
        for key in ('title', 'date') + (('category',) if section == 'blog' else ()):
            if not meta.get(key):
                raise ValueError(f'{source.name}: missing {key}')
        dt.date.fromisoformat(meta['date'])
        if section == 'blog' and meta['category'] not in BLOG_CATEGORIES:
            raise ValueError(f'{source.name}: category must be 论文精读, 概念理解 or 碎碎念')
        if section == 'life':
            meta['category'] = '生活记录'
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', source.stem):
            raise ValueError(f'{source.name}: use an English filename, such as my-first-post.md')
        paper_path = source.with_suffix('.json')
        paper = json.loads(paper_path.read_text(encoding='utf-8-sig')) if paper_path.exists() else None
        posts.append({**meta, 'section': section, 'slug': source.stem, 'body': parts[2].strip(), 'paper': paper})
    return sorted(posts, key=lambda post: (post['date'], post['slug']), reverse=True)


def post_path(post: dict) -> str:
    directory = 'post' if post['section'] == 'blog' else 'life'
    return f'{directory}/{post["slug"]}/index.html'


def paper_figure(figure: dict, prefix: str) -> str:
    relative = figure['image'].lstrip('/')
    version = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()[:12]
    src = ESC(prefix + relative + '?v=' + version, quote=True)
    caption = ESC(figure['caption'])
    caption_en = ESC(figure['caption_en'])
    source = ''
    if figure.get('source'):
        source_label = ESC(figure.get('source_label', 'Zhang et al. (2024)'))
        source = '<span class="figure-source"><a href="' + ESC(figure['source'], quote=True) + '">' + source_label + '</a> · ' + ESC(figure['locator']) + ' · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a></span>'
    wrapper = 'class="figure-image"'
    if figure.get('rotate') == -90:
        width, height = int(figure['width']), int(figure['height'])
        wrapper = f'class="figure-image quarter-turn" style="aspect-ratio:{height}/{width};--scan-width:{100 * width / height:.6f}%"'
    figure_style = f' style="max-width:{int(figure["max_width"])}px;margin-inline:auto"' if figure.get('max_width') else ''
    return f'''<figure class="paper-figure" id="{ESC(figure['id'], quote=True)}"{figure_style}><div {wrapper}><img src="{src}" alt="{caption} / {caption_en}" width="{figure['width']}" height="{figure['height']}" loading="lazy"></div><figcaption>{caption}<span class="translation" lang="en">{caption_en}</span>{source}</figcaption></figure>'''


def paper_metadata(paper: dict) -> str:
    names = ' · '.join(ESC(author['name']) for author in paper['authors'])
    emails = ''.join('<li>' + ESC(author['name']) + '：<a href="mailto:' + ESC(author['email'], quote=True) + '">' + ESC(author['email']) + '</a></li>' for author in paper['authors'] if author.get('email'))
    links = ' · '.join('<a href="' + ESC(link['url'], quote=True) + '">' + ESC(link['label']) + '</a>' for link in paper['links'])
    keywords = ''.join('<li>' + ESC(item['zh']) + ('<span lang="en"> / ' + ESC(item['en']) + '</span>' if item['zh'] != item['en'] else '') + '</li>' for item in paper['keywords'])
    affiliations = '<br>'.join(ESC(item['zh']) + ' · <span lang="en">' + ESC(item['en']) + '</span>' for item in paper.get('affiliations', [{'zh': '北京大学', 'en': 'Peking University'}]))
    corresponding = ESC(paper.get('corresponding_author', 'Yansong Feng'))
    return f'''<section class="paper-details" aria-label="论文信息 · Paper information"><dl class="paper-metadata"><dt>作者 · <span lang="en">Authors</span></dt><dd>{names}<br>{affiliations}<br><span class="meta">通讯作者 · <span lang="en">Corresponding author</span>：{corresponding}</span></dd><dt>作者邮箱 · <span lang="en">Author emails</span></dt><dd><ul class="author-emails">{emails}</ul></dd><dt>发表信息 · <span lang="en">Publication</span></dt><dd><span lang="en">{ESC(paper['venue'])}</span><br>{ESC(paper['publication_details'])}</dd><dt>链接 · <span lang="en">Links</span></dt><dd>{links}</dd><dt>关键词 · <span lang="en">Keywords</span></dt><dd><ul class="paper-keywords">{keywords}</ul></dd></dl></section>'''


def paper_references(paper: dict) -> str:
    entries = []
    for reference in paper['references']:
        entries.append('<li id="ref-' + ESC(reference['id'], quote=True) + '">' + ESC(reference['authors']) + '. ' + ESC(reference['year']) + '. <a href="' + ESC(reference['url'], quote=True) + '">' + ESC(reference['title']) + '</a>. ' + ESC(reference['publication']) + '.</li>')
    return '<section class="paper-references" aria-labelledby="references-title"><h2 id="references-title">参考文献 · <span lang="en">References</span></h2><ol>' + ''.join(entries) + '</ol></section>'


def page(title: str, body: str, path: str, section: str, description: str | None = None) -> str:
    depth = len(Path(path).parts) - 1
    prefix = '../' * depth
    if path == '404.html':
        prefix = CONFIG['url'].rstrip('/') + '/'
    home_href = prefix or './'

    def asset_url(relative: str) -> str:
        version = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()[:12]
        return ESC(prefix + relative + '?v=' + version, quote=True)

    nav = []
    for label, target, key in [
        (bilingual('主页'), '', 'home'),
        (bilingual('博客'), 'post/index.html', 'blog'),
        (bilingual('生活'), 'life/index.html', 'life'),
    ]:
        current = ' aria-current="page"' if key == section else ''
        href = home_href if key == 'home' else prefix + target
        home_attribute = ' data-home-link' if key == 'home' else ''
        nav.append(f'<li><a href="{href}"{current}{home_attribute}><svg class="bookmark" viewBox="0 0 10 14" aria-hidden="true"><path d="M1 1h8v11l-4-3-4 3Z"/></svg><span class="nav-text">{label}</span></a></li>')
    name = ESC(CONFIG['name'])
    name_en = ESC(CONFIG['name_en'])
    desc = ESC(CONFIG['description'])
    desc_en = ESC(CONFIG['description_en'])
    canonical = CONFIG['url'].rstrip('/') + '/' + ('' if path == 'index.html' else path.removesuffix('index.html'))
    page_title = CONFIG['name'] + ' · ' + CONFIG['name_en'] if section == 'home' else title + (' · ' + EN[title] if title in EN else '') + ' | ' + CONFIG['name'] + ' · ' + CONFIG['name_en']
    meta_description = (description or CONFIG['description']) + ' ' + CONFIG['description_en']
    math_assets = ''
    if 'data-tex=' in body:
        math_assets = f'''<link rel="stylesheet" href="{asset_url('assets/vendor/katex/katex.min.css')}">
  <script src="{asset_url('assets/vendor/katex/katex.min.js')}" defer></script>
  <script src="{asset_url('assets/math.js')}" defer></script>'''
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{ESC(page_title)}</title>
  <meta name="description" content="{ESC(meta_description, quote=True)}">
  <meta name="theme-color" content="#fefefe">
  <meta property="og:title" content="{ESC(page_title, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:description" content="{ESC(meta_description, quote=True)}">
  <meta property="og:url" content="{ESC(canonical, quote=True)}">
  <link rel="canonical" href="{ESC(canonical, quote=True)}">
  <link rel="icon" href="{asset_url('assets/favicon.svg')}" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{name}的博客 · {name_en}'s Blog" href="{prefix}feed.xml">
  <script src="{asset_url('assets/theme.js')}"></script>
  <link rel="stylesheet" href="{asset_url('assets/style.css')}">
  <script src="{asset_url('assets/main.js')}" defer></script>
  {math_assets}
</head>
<body>
  <a class="skip-link" href="#main">跳转到正文 · <span lang="en">Skip to content</span></a>
  <header class="sidebar">
    <div class="intro">
      <a class="avatar-link" href="{home_href}" data-home-link aria-label="{name}的首页 · {name_en}'s home"><img class="avatar" src="{asset_url(CONFIG['avatar'])}" alt="{name}的照片 · Photo of {name_en}" width="1706" height="1279"></a>
      <div><p class="sidebar-description">{name}，{desc}</p><p class="sidebar-description-en" lang="en">{name_en}. {desc_en}</p><a class="sidebar-github" href="{CONFIG['github']}">GitHub · 2245243969</a><a class="sidebar-email" href="mailto:{ESC(CONFIG['email'], quote=True)}" aria-label="QQ 邮箱 · QQ Email: {ESC(CONFIG['email'], quote=True)}">{ESC(CONFIG['email'])}</a><a class="sidebar-bilibili" href="{ESC(CONFIG['bilibili'], quote=True)}" target="_blank" rel="noopener noreferrer">{bilingual('B站主页')}</a></div>
    </div>
    <nav class="navigation" aria-label="主导航 · Main navigation">
      <button class="menu-button" id="menu-button" aria-expanded="false" aria-controls="navigation-list">菜单 · Menu <span data-menu-state aria-hidden="true">+</span></button>
      <ul id="navigation-list">{''.join(nav)}</ul>
    </nav>
  </header>
  <div class="main-and-footer"><div class="page">
    <main id="main" tabindex="-1">{body}</main>
    <footer class="footer">
      <label class="theme-label" for="themer">深色主题 · <span lang="en">Dark theme:</span> <input type="checkbox" id="themer" aria-label="深色主题 · Dark theme"><span id="theme-state" aria-hidden="true">关 · Off</span></label>
      <p>{name} <span lang="en">/ {name_en}</span> · <a href="{CONFIG['github']}">GitHub</a> · <a href="mailto:{ESC(CONFIG['email'], quote=True)}">{bilingual('QQ 邮箱')}</a> · <a href="{ESC(CONFIG['bilibili'], quote=True)}" target="_blank" rel="noopener noreferrer">{bilingual('B站主页')}</a> · <a href="{prefix}feed.xml">RSS</a></p>
      <p class="footer-note">个人主页 · 学习与生活<span class="translation" lang="en">Personal Website · Learning &amp; Life</span></p>
    </footer>
  </div></div>
</body>
</html>
'''


def post_list(posts: list[dict], prefix: str) -> str:
    if not posts:
        return '<div class="empty"><p>还没有发布文章。<span class="translation" lang="en">No articles have been published yet.</span></p></div>'
    rows = []
    for post in posts:
        summary_en = '<span class="translation" lang="en">' + ESC(post['summary_en']) + '</span>' if post.get('summary_en') else ''
        rows.append(f'''<li><h2 class="post-title"><a href="{prefix}{post_path(post)}">{ESC(post['title'])}</a></h2><p class="meta"><time datetime="{post['date']}">{post['date']}</time> · {bilingual(post['category'])}</p><p>{ESC(post.get('summary', ''))}{summary_en}</p></li>''')
    return '<ul class="post-list">' + ''.join(rows) + '</ul>'


def build(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'assets').resolve() != (ROOT / 'assets').resolve():
        shutil.copytree(ROOT / 'assets', destination / 'assets', dirs_exist_ok=True)
    posts = load_posts()
    blog_posts = [post for post in posts if post['section'] == 'blog']
    life_posts = [post for post in posts if post['section'] == 'life']
    life_empty = '<div class="empty"><p>暂无生活记录。<span class="translation" lang="en">No life updates yet.</span></p></div>'
    pages: dict[str, tuple[str, str, str]] = {}
    home = f'''<h1>{ESC(CONFIG['name'])}<span class="name-en" lang="en">{ESC(CONFIG['name_en'])}</span></h1>
<div class="bio"><p>{ESC(CONFIG['description'])}</p><p class="translation" lang="en">{ESC(CONFIG['description_en'])}</p></div>
<p>GitHub：<a href="{CONFIG['github']}">github.com/2245243969</a></p>
<p>{bilingual('QQ 邮箱')}：<a href="mailto:{ESC(CONFIG['email'], quote=True)}">{ESC(CONFIG['email'])}</a></p>
<p>{bilingual('B站主页')}：<a href="{ESC(CONFIG['bilibili'], quote=True)}" target="_blank" rel="noopener noreferrer">space.bilibili.com/289847537</a></p>
<h2>{bilingual('博客')}：</h2>
{post_list(blog_posts[:3], '')}
<p class="section-link"><a href="post/index.html">{bilingual('浏览博客')} →</a></p>
<h2>{bilingual('生活')}：</h2>
{post_list(life_posts[:3], '') if life_posts else life_empty}'''
    pages['index.html'] = (CONFIG['name'], home, 'home')
    blog_filters = list(BLOG_CATEGORIES.items())
    for path, title, selected, category in [
        ('post/index.html', '博客', 'blog', None),
        *[(target, label, 'blog', label) for label, target in blog_filters],
    ]:
        prefix = '../' * (len(Path(path).parts) - 1)
        links = ''.join(f'<li><a href="{prefix}{target}"' + (' aria-current="page"' if target == path else '') + f'>{bilingual(label)}</a></li>' for label, target in blog_filters)
        filtered = [post for post in blog_posts if category is None or post['category'] == category]
        body = f'<h1>{bilingual(title)}</h1>' + notes_intro() + f'<ul class="filters" aria-label="文章分类 · Article categories">{links}</ul>' + post_list(filtered, prefix)
        pages[path] = (title, body, selected)
    pages['life/index.html'] = ('生活', '<h1>' + bilingual('生活') + '</h1>' + (post_list(life_posts, '../') if life_posts else life_empty), 'life')
    for post in posts:
        section = post['section']
        parent = '../index.html' if section == 'life' else '../../' + BLOG_CATEGORIES[post['category']]
        paper = post.get('paper')
        content = markdown(post['body'], '../../', paper.get('figures') if paper else None)
        if paper and paper.get('kind') not in ('concept', 'musing'):
            originals = ''.join(paper_figure(figure, '../../') for figure in paper['handwritten'])
            content = paper_metadata(paper) + '<section class="notes-original" aria-labelledby="notes-title"><h2 id="notes-title">笔记正文 · <span lang="en">Notes</span></h2>' + content + '</section>' + paper_references(paper) + '<section class="handwritten-originals" aria-labelledby="handwritten-title"><h2 id="handwritten-title">手稿原图 · <span lang="en">Original Handwritten Notes</span></h2>' + originals + '</section>'
        elif paper:
            videos = ''.join('<li><a href="' + ESC(video['url'], quote=True) + '" target="_blank" rel="noopener noreferrer">' + ESC(video['label']) + '</a></li>' for video in paper.get('reference_videos', []))
            if videos:
                content += '<section class="paper-references"><h2>参考视频 · <span lang="en">Reference Videos</span></h2><ol>' + videos + '</ol></section>'
            originals = ''.join(paper_figure(figure, '../../') for figure in paper.get('handwritten', []))
            if originals:
                content += '<section class="handwritten-originals" aria-labelledby="handwritten-title"><h2 id="handwritten-title">手稿原图 · <span lang="en">Original Handwritten Notes</span></h2>' + originals + '</section>'
        body = f'<a class="back-link" href="{parent}">← {bilingual("返回文章列表")}</a><article class="article"><h1>{ESC(post["title"])}</h1><p class="meta"><time datetime="{post["date"]}">{post["date"]}</time> · {bilingual(post["category"])}</p>' + content + '</article>'
        pages[post_path(post)] = (post['title'], body, section)
    pages['404.html'] = ('页面未找到', '<h1>' + bilingual('页面未找到') + '</h1><p>这个页面可能已经移动，或链接有误。</p><p class="translation" lang="en">This page may have moved, or the link may be incorrect.</p><p><a href="' + CONFIG['url'] + '/">' + bilingual('返回首页') + ' →</a></p>', '')
    for path, (title, body, section) in pages.items():
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page(title, body, path, section), encoding='utf-8')
    (destination / '.nojekyll').touch()
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', CONFIG['name'] + '的博客 · ' + CONFIG['name_en'] + "'s Blog"), ('link', CONFIG['url']), ('description', '论文精读、概念理解与碎碎念 · Paper deep dives, concept notes, and random thoughts'), ('language', 'zh-CN')]:
        ET.SubElement(channel, key).text = value
    for post in blog_posts:
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
