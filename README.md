# 《走出戈壁》文字整理与阅读资源

本项目基于单伟健《走出戈壁》扫描本整理，提供简繁体文字稿、EPUB 与文字重排 PDF、原书图片和离线阅读器，另收录一份实验性人物传记地图。

**本项目仅供学习与参考，所提供的整理版为非正式出版物。**

## 阅读与下载

### 电子书

提供四种阅读文件：简体 EPUB、简体 PDF、繁体 EPUB、繁体 PDF。

- **独立文件下载**：[book-v1.0 Release](https://github.com/Always1010/Out_of_the_Gobi/releases/tag/book-v1.0) 已发布，四份文件可分别下载：
  - 简体：[EPUB](https://github.com/Always1010/Out_of_the_Gobi/releases/download/book-v1.0/out-of-the-gobi-zh-Hans.epub) · [PDF](https://github.com/Always1010/Out_of_the_Gobi/releases/download/book-v1.0/out-of-the-gobi-zh-Hans.pdf)
  - 繁体：[EPUB](https://github.com/Always1010/Out_of_the_Gobi/releases/download/book-v1.0/out-of-the-gobi-zh-Hant.epub) · [PDF](https://github.com/Always1010/Out_of_the_Gobi/releases/download/book-v1.0/out-of-the-gobi-zh-Hant.pdf)
- **构建备份**：[已成功的 Actions 运行](https://github.com/Always1010/Out_of_the_Gobi/actions/runs/38091928739) 的 Artifacts 中保留四书及校验文件。需登录 GitHub；产物请求保留 90 天，以仓库策略为限。
- **版本来源**：本版包含诗句逗号和原书漏句号两处最新修订。四个 Release 文件已下载校验 SHA-256，并通过正文、卷首、图片及连续页码检查；根目录四份旧成品已移除，源码与构建程序保留。

后续版本使用新 `book-v*` 标签触发构建与发布；手动补发已有标签时填写 `release_tag`。详见[电子书构建与发布说明](book_reader/BUILD_EBOOKS.md)。

### 文字稿与离线阅读

- 直接阅读：[简体连续稿](book_reader/text/book-simplified-continuous.md) · [繁体连续稿](book_reader/text/book-traditional-continuous.md)。
- 回查原页：[简体分页稿](book_reader/text/book-simplified.md) · [繁体分页稿](book_reader/text/book-traditional.md)，保留原扫描 PDF 页码定位。
- 离线阅读器：按下方命令生成后，在本地打开 `book_reader/site/dist/index.html`，支持目录、全文搜索、字体与主题设置、阅读进度及图片放大。

## 校对与修订说明

全书文字稿已完成校对与修订，已确认的转写、繁简转换、段落结构及图注问题已修正；原书自身仍存疑的内容予以保留并另作说明。

**整理版仍可能存在错字、漏字、标点、排版或图片标注偏差。**如发现问题，请在 [Issues](https://github.com/Always1010/Out_of_the_Gobi/issues) 中注明文件名、章节、问题片段和建议更正；如方便，也请附原扫描页码。

- [本次修改说明](book_reader/qa/本次修改说明.md)：修改范围、卷首恢复、页码处理及成品交付状态。
- [原文疑点说明](book_reader/qa/原文疑点说明.md)：保留的原书疑点及处理依据。

## 项目目录与文档

| 路径 | 内容 |
| --- | --- |
| `book_reader/text/` | 简繁体分页稿、连续稿、全书汇编及卷首内容 |
| `book_reader/ocr/` | 420 个 PDF 物理页的原始 OCR 结果、逐页文本和索引 |
| `book_reader/images/` | 原书图片、卷首原图、图注与图片清单 |
| `book_reader/scripts/` | 文字稿整理、电子书及阅读器构建、校验脚本 |
| `book_reader/qa/` | 修改说明、疑点记录、校改清单与核验记录 |
| `book_reader/output/` | 本地生成的 EPUB/PDF，不纳入 Git |
| `biography/` | 实验性人物传记地图及相关资料 |

处理流程见 [book_reader/README.md](book_reader/README.md)，构建与发布见 [BUILD_EBOOKS.md](book_reader/BUILD_EBOOKS.md)，原 OCR 环境记录见 [OCR环境.md](book_reader/OCR环境.md)。

## 本地重建

先按[构建说明](book_reader/BUILD_EBOOKS.md#本地复现)准备 Python 环境与依赖，再在仓库根目录运行以下命令，从已校对分页稿生成连续稿和离线阅读器：

```sh
python book_reader/scripts/build_continuous_transcript.py
python book_reader/scripts/build_reader_site.py
```

随后打开 `book_reader/site/dist/index.html`。电子书的依赖、字体准备及完整构建校验步骤见[构建说明](book_reader/BUILD_EBOOKS.md#本地复现)。

原扫描文件 `走出戈壁-单伟健.pdf` 不随 Git 提交；仅从现有校订稿重建电子书和阅读器不需要该文件，阅读器跳转原扫描页时需在本地保留它。依赖、模型、下载缓存和临时文件由 `.gitignore` 排除。

## 人物传记地图（实验性）

人物传记地图由 GPT-6.Astra 尝试制作，效果尚不理想，仅供参考。下载项目后，可在本地打开 [biography/dist/index.html](biography/dist/index.html)，浏览原书经历及相关人物、地图和场景。

使用、重建与校验方式见 [biography/README.md](biography/README.md)，当前设计见 [biography/NODE_MAP.md](biography/NODE_MAP.md)。
