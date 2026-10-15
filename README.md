# 张育玮的个人网站

按照参考站 https://polarlion.github.io/ 的左侧导航、右侧正文、黑白排版制作，使用你自己的个人信息、GitHub 头像与公开项目。保留深色主题和手机菜单，增加作品详情、博客分类和生活记录。

个人介绍：东北财经大学2023年级大四在读生，人工智能专业。

## 第一次发布到 GitHub Pages

1. 登录 https://github.com/2245243969 ，创建一个 **Public** 仓库，名字必须是 **2245243969.github.io**，默认分支使用 **main**。
2. 将本文件所在目录的全部内容放到仓库根目录。`index.html`、`build.py`、`site.json`、`assets`、`content`、`.github` 应当直接出现在仓库根目录；不要再套一层同名文件夹。
3. 打开仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。
4. 在 **Actions** 中打开 **Deploy personal site to GitHub Pages**，点击 **Run workflow → Run workflow**。之后每次推送到 main 分支会自动重新发布。
5. 工作流成功后访问 **https://2245243969.github.io/**。这是发布后的目标地址，源码包本身不代表网站已经上线。

注意：`.github/workflows/pages.yml` 是自动构建的配置，请一并上传。Windows 文件管理器需要开启“隐藏的项目”才能看到点开头的文件夹。

如果使用 Git，在这个目录中执行：

```sh
git init -b main
git add .
git commit -m "Create personal website"
git remote add origin https://github.com/2245243969/2245243969.github.io.git
git push -u origin main
```

上述命令适用于新建的空仓库。如果仓库已有内容，请先克隆已有仓库，再复制网站文件进去提交，避免覆盖原有内容。

## 本地预览

可以直接双击 `index.html` 查看，也可以用 Python 3.10 及以上版本启动预览：

```sh
python build.py
python -m http.server 8000 --directory _site
```

打开 http://localhost:8000/ 。预览时不用安装任何 Python 第三方依赖。

## 修改个人信息与作品

- `site.json`：姓名、介绍、GitHub 地址、正式网址、头像路径。
- `assets/avatar.png`：你的 GitHub 头像快照，可以用自己的照片替换。
- `content/projects.json`：作品名称、简介、详情、源码仓库和是否在首页精选。
- `assets/style.css`：排版与响应式样式。

公开项目依据 GitHub 仓库整理，不包含虚构的工作经历、论文、邮箱或获奖信息。网站尚未提供真实文章，所以博客与生活记录初始为空。

## 写一篇博客

复制 `content/posts/_template.md` 为 `content/posts/my-first-post.md`，使用英文、数字、短横线组成文件名。示例：

```markdown
---
title: 我的第一篇文章
date: 2026-10-15
category: 学习笔记
summary: 这篇文章的简短介绍。
draft: false
---

## 一个小标题

在这里写正文。
```

`category` 使用 **学习笔记** 或 **生活随笔**。生活随笔会同时出现在博客总列表与生活页面。`draft: true` 的文章不会发布，下划线开头的文件也不会发布。

支持常用 Markdown：段落、标题、粗体、斜体、行内代码、代码块、列表、链接、图片与引用。不支持复杂 Markdown 扩展或正文中的原始 HTML。日期不会自动阻止未来文章发布；计划发布前请保持草稿状态。

图片放入 `assets/images/`，文章中使用 `![图片说明](/assets/images/文件名.jpg)`。更新后推送 GitHub，工作流自动构建，无须手动生成文章 HTML。

本地重新生成可双击预览的根目录页面，运行 `python build.py --output .`。正式部署由工作流从内容文件重新生成 `_site`，根目录预生成页面仅方便第一次预览。

## 参考与实现

视觉参考：https://polarlion.github.io/ 。页面布局与代码重新实现，未复制参考站的个人照片、履历、论文或文章。此版本无第三方运行时资源依赖，无访问统计脚本；网站内容可直接托管在 GitHub Pages。

发布配置参考 GitHub 官方文档：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages 。
