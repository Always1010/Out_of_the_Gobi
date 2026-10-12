# GitHub Pages 阅读网站

网站由静态介绍首页和简体阅读器组成，PDF / EPUB 继续从 GitHub Releases 下载。

| 地址 | 内容 |
| --- | --- |
| `https://always1010.github.io/Out_of_the_Gobi/` | 项目介绍、在线阅读入口、简繁体 PDF / EPUB 下载 |
| `https://always1010.github.io/Out_of_the_Gobi/read/` | 简体在线阅读器 |
| `https://always1010.github.io/Out_of_the_Gobi/sitemap.xml` | 首页和阅读器的站点地图 |

这些地址在首次成功部署后可用。代码提交到本地不会自动上线，必须先将相应提交上传到 GitHub。

## 首次上线

1. 在 GitHub 仓库打开 **Settings → Pages**，将 **Build and deployment → Source** 设置为 **GitHub Actions**。
2. 将本次网站改动推送到远程 `main`。按项目协作规则，执行远程 push 必须由用户明确授权。
3. 在 **Actions** 查看 **Deploy reading site to GitHub Pages**。首次推送会触发；也可点 **Run workflow**，选择 `main` 手动运行。
4. 确认 `build` 和 `deploy` 均成功，打开部署任务显示的 URL，检查首页、“开始在线阅读”、图片、搜索和下载链接。
5. 将网站地址填写到仓库首页的 **About → Website**，并补充描述与 Topics。

工作流只从 `main` 部署。其他分支手动运行只构建产物，不更新线上网站。如 `configure-pages` 报站点不存在，先检查第 1 步；如部署等待批准，检查 `github-pages` 环境的保护规则。

## 构建与更新

- 首页源码：`web/index.html`、`web/styles.css`。主要介绍、下载和阅读链接直接写在 HTML 中，不依赖 JavaScript。
- 阅读器源码：`book_reader/scripts/build_reader_site.py`，正文、图片和图注来自已提交的校订稿与原书图片。
- 发布组装：`book_reader/scripts/build_pages_site.py`，生成 `_site/`，包含首页、`read/`、`sitemap.xml` 和 `.nojekyll`。
- 字体准备：`book_reader/scripts/prepare_reader_fonts.py`，沿用电子书工作流固定的官方来源与 SHA-256，生成静态字重；只写入构建缓存，不安装系统字体。
- 部署工作流：`.github/workflows/deploy-pages.yml`，在远端 Ubuntu runner 安装三项阅读器构建依赖，构建并检查文件引用后发布 `_site/`。不构建 PDF / EPUB，不重新执行 OCR，也不改写书稿。

更新首页、书稿、图片或构建脚本并推送到 `main`，会自动部署。只改 README 或部署说明不会触发构建；需要时手动运行工作流。首页四份电子书使用 `releases/latest/download/` 链接，自动跟随 GitHub 标记的最新正式 Release，无需逐版修改首页。后续 Release 须继续提供 `out-of-the-gobi-zh-Hans.pdf`、`out-of-the-gobi-zh-Hans.epub`、`out-of-the-gobi-zh-Hant.pdf`、`out-of-the-gobi-zh-Hant.epub` 四个同名附件，并保持为最新正式发布。

`_site/`、阅读器 `dist/`、字体缓存和本地成品不纳入 Git。首页和在线阅读器使用白底、黑灰文字；首页不放图片，在线产物不包含书籍封面。发布产物仅含网站所需文件，构建校验会检查 HTML / CSS 引用、章节图片、字体及站点地图；缺少文件时停止发布。原扫描 PDF 不上传，在线版“项目首页与下载”回到首页；默认离线版继续保留原扫描页跳转及封面。

## Google Search Console

1. 部署成功后，在 Search Console 添加“网址前缀”属性：`https://always1010.github.io/Out_of_the_Gobi/`。
2. 选择 HTML 标签验证，复制 `google-site-verification` 标签中 **content 的值**。
3. 在 GitHub **Settings → Secrets and variables → Actions → Variables** 创建 Repository variable：`GOOGLE_SITE_VERIFICATION`，值填写第 2 步的字符串。不要粘贴整个标签。这个验证值会公开出现在首页 HTML 中。
4. 手动运行 Pages 工作流。上线后检查首页源码中的验证标签，再回 Search Console 完成验证。
5. 提交 `sitemap.xml`，用“网址检查”检查首页和 `/read/`，按需请求编入索引。收录与排名由 Google 决定，成功部署不代表已经收录。

项目网站带有首页与阅读器各自的 canonical URL；工作流使用 Pages 配置返回的实际站点地址，自定义域名也按该地址生成。站点地图不包含阅读器的章节 hash，章节目前共享同一个页面 URL。`robots.txt` 的作用范围是域名根目录，本项目不在仓库子路径放置无效的 robots 文件。

## 本地重建与预览

需要 Python 3.12 和阅读器依赖。已有环境可直接使用；下面的安装命令供自行准备环境，不是部署到 GitHub 的前置本机要求：

```powershell
python -m pip install -r book_reader/requirements-reader.txt
python book_reader/scripts/prepare_reader_fonts.py cache/pages-fonts
$env:GOBI_FONT_SC = (Resolve-Path cache/pages-fonts/NotoSansSC-Regular.ttf).Path
$env:GOBI_SERIF_SC = (Resolve-Path cache/pages-fonts/NotoSerifSC-Regular.ttf).Path
$env:GOBI_LEADIN_SC = (Resolve-Path cache/pages-fonts/LXGWWenKai-Light.ttf).Path
python book_reader/scripts/build_pages_site.py
python -m http.server 8000 --bind 127.0.0.1 --directory _site
```

打开 `http://127.0.0.1:8000/` 和 `http://127.0.0.1:8000/read/`。这三个环境变量仅在当前 PowerShell 会话中生效。字体准备会下载固定来源并验证哈希，不修改本机字体目录；脚本默认直接读取已提交的连续稿，修改分页校订稿后请先按主 README 的流程重新生成连续稿。

如要以不同线上地址构建，可使用 `--site-url https://example.com/project/`；可选 `--google-verification 验证值` 用于本地检查验证标签。`build_pages_site.py` 每次只替换仓库根目录的 `_site/`，不接受任意输出目录。
