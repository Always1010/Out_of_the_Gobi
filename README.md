# 《走出戈壁》文字整理与人物传记地图

项目保存全书扫描版的文字稿、原书图片和本地阅读器，另包含一份实验性人物传记地图。

**本项目仅作为学习和参考用途，项目中书籍皆为非正式出版或经过完整人工校订的版本。**

## 全书资料

- `book_reader/ocr/`：420 个 PDF 物理页的 OCR JSON、逐页文本和索引。
- `book_reader/text/`：33 节繁简体、分页及连续 Markdown，包含完整汇编；分页稿保留 PDF 页码，适合回查证据。
- `book_reader/images/`：21 个实际图片页，15 页可辨图注。
- `book_reader/output/`：被 Git 忽略的电子书生成目录；主目录中的四个电子书文件是纳入 Git 的成品。
- `book_reader/site/dist/index.html`：本机生成的离线阅读器。
- `book_reader/qa/full-manuscript-review.md`：文字稿复核结论；全书尚未完成逐字人工校勘。

阅读器与全书处理说明见 [book_reader/README.md](book_reader/README.md)，已安装的 OCR 工具路径见 [book_reader/OCR环境.md](book_reader/OCR环境.md)。

## 电子书成品

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
