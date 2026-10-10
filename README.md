# 《走出戈壁》文字整理与人物传记地图

项目保存全书扫描版的文字稿、原书图片和本地阅读器，另包含一份实验性人物传记地图。

**本项目仅作为学习和参考用途，项目中书籍皆为非正式出版或经过完整人工校订的版本。**

## 全书资料

- `book_reader/ocr/`：420 个 PDF 物理页的 OCR JSON、逐页文本和索引。
- `book_reader/text/`：33 节正文及前后附录、2 节卷首的繁简体文字，含分页稿、连续稿及全书汇编；分页稿保留 PDF 页码，适合回查证据。
- `book_reader/images/`：22 个封面／题字／正文图片页、2 张新增卷首原图，16 页可辨图注。
- `book_reader/output/`：被 Git 忽略的电子书生成目录；主目录中的四个电子书文件是纳入 Git 的成品。
- `book_reader/site/dist/index.html`：本机生成的离线阅读器。
- `book_reader/qa/full-manuscript-review.md`：文字稿复核结论；全书尚未完成逐字人工校勘。

本次原扫描回改见[本次修改说明](book_reader/qa/本次修改说明.md)与[原文疑点说明](book_reader/qa/原文疑点说明.md)。已确认的转写差异已修复；原书自身疑点保留。

阅读器与全书处理说明见 [book_reader/README.md](book_reader/README.md)，已安装的 OCR 工具路径见 [book_reader/OCR环境.md](book_reader/OCR环境.md)。

## 电子书成品

**根目录 EPUB/PDF 尚为改前版本，请勿作为本次校订成品下载。**校订源码已就绪；新增 [Tag 打包工作流](book_reader/BUILD_EBOOKS.md)，合入后推送 `book-v*` 标签即可由 GitHub Runner 重建简体／繁体 EPUB 与 PDF，并从 Actions 下载四份成品。工作流首次实际运行需在合入并触发后确认。

下面四个链接保留为旧版存档；新校订版请使用上述 Actions 产物。详见[本次修改说明](book_reader/qa/本次修改说明.md#电子书交付状态)。

| 版本 | EPUB | 文字重排 PDF |
| --- | --- | --- |
| 简体 | [走出戈壁-简体.epub](走出戈壁-简体.epub) | [走出戈壁-简体.pdf](走出戈壁-简体.pdf) |
| 繁体 | [走出戈壁-繁体.epub](走出戈壁-繁体.epub) | [走出戈壁-繁体.pdf](走出戈壁-繁体.pdf) |

这些成品由 OCR 文字稿生成，**尚未经过人工逐字审稿**，可能存在错字、漏字、标点、排版或图注偏差。如发现问题，请在项目 Issues 中说明文件名、章节、问题片段和建议更正。

## 人物传记地图（实验性）

人物传记地图是让 GPT-6.Astra 尝试制作的练习性内容，**效果并不理想**，仅供参考。打开 [biography/dist/index.html](biography/dist/index.html)，可离线浏览原书经历及相关地图、人物和场景。

当前带读方案见 [biography/GUIDED_READING.md](biography/GUIDED_READING.md)，重建与校验方式见 [biography/README.md](biography/README.md)。

## 重建阅读器

```powershell
python book_reader/scripts/build_reader_site.py
```

随后打开 `book_reader/site/dist/index.html`。本机原 PDF 为 `走出戈壁-单伟健.pdf`，不随 Git 提交。依赖、模型、下载缓存和临时文件均在 `.gitignore` 中排除。
