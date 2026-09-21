# 《走出戈壁》扫描版文字整理与知识图谱

本项目从《走出戈壁》的图片型 PDF 提取文字，保留逐页 OCR 证据，整理繁体、简体文字稿，并探索带原文出处的知识图谱。当前已有全书文字整理和前 20 页图谱试点。

## 当前进度

- 420 个 PDF 物理页均有逐页 OCR 结果及处理索引；OCR 完成不代表文字已经逐字校对。
- 已生成 33 个章节或前后附录的繁体、简体 Markdown，以及全书合并稿。
- 已登记 22 个包含封面、照片或其他图片内容的页面，保存阅读器所需图像。
- 前 20 页试点图谱包含 65 个节点、67 条关系，每条关系记录 PDF 页码和书中引文。全书图谱仍待扩展。
- 离线阅读器的构建脚本和本机生成的页面已存在；人工校对和完整性验收仍需继续。

## 目录

| 路径 | 内容 |
| --- | --- |
| `book_reader/scripts/` | 全书 OCR、文字组装、图片处理、离线阅读器构建脚本 |
| `book_reader/ocr/` | 420 页的 OCR JSON、逐页文本及处理索引 |
| `book_reader/text/` | 章节目录、繁简体分章稿及合并稿 |
| `book_reader/images/` | 图片页清单与阅读器使用的图片 |
| `book_reader/site/` | 阅读器说明与静态站点配置；`dist/` 为可重建输出 |
| `pilot20/` | 前 20 页 OCR 对照、图谱数据、构建脚本和离线图谱页面 |
| `OCR安装与资源规划.md` | 本机 OCR 安装、资源占用与试点实测 |

更详细的处理流程见 [`book_reader/README.md`](book_reader/README.md)；图谱试点的页码范围和质量说明见 [`pilot20/README.md`](pilot20/README.md)。

## 在本机查看与重建

图谱试点可直接用浏览器打开 `pilot20/site/index.html`。前 20 页的扫描预览图保存在 `pilot20/tmp/page-*.png`，用于从关系证据跳转原页。

阅读器的构建脚本只使用 Python 标准库，可在仓库根目录运行：

```powershell
python book_reader/scripts/build_reader_site.py
```

随后打开 `book_reader/site/dist/index.html`。构建脚本读取仓库中的简体章节稿和图片，并生成完整的离线站点。试点图谱可用以下命令从已保存的 OCR 文本重新构建：

```powershell
python pilot20/build_graph.py
python pilot20/build_site.py
```

重新执行全书 OCR 或文字组装需要本地 Python 依赖和原始 PDF。原书文件应放在仓库根目录，文件名为 `走出戈壁-单伟健.pdf`；安装与运行记录见 [`OCR安装与资源规划.md`](OCR安装与资源规划.md)。

## Git 收录范围

仓库保留脚本、逐页 OCR、文字稿、图谱数据，以及直接查看试点和重建阅读器所需的图片。`.gitignore` 排除本机虚拟环境、下载的模型、缓存、日志、临时文件、拼页总览图、重复生成的 `book_reader/site/dist/` 和原始 PDF。原书 PDF 保留在本机，不随 Git 提交。
