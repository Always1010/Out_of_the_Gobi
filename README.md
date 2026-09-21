# 《走出戈壁》文字整理与人物传记地图

项目保存全书扫描版的文字稿、原书图片和本地阅读器，并以原书为基础设计交互式人物传记地图。2026-09-22 已按用户要求删除旧的前 20 页试点及知识图谱。

## 全书资料

- `book_reader/ocr/`：420 个 PDF 物理页的 OCR JSON、逐页文本和索引。
- `book_reader/text/`：33 节繁简体、分页及连续 Markdown，包含完整汇编；分页稿保留 PDF 页码，适合回查证据。
- `book_reader/images/`：21 个实际图片页，15 页可辨图注。
- `book_reader/site/dist/index.html`：本机生成的离线阅读器。
- `book_reader/qa/full-manuscript-review.md`：文字稿复核结论；全书尚未完成逐字人工校勘。

阅读器与全书处理说明见 [book_reader/README.md](book_reader/README.md)，已安装的 OCR 工具路径见 [book_reader/OCR环境.md](book_reader/OCR环境.md)。

## 人物传记地图

打开 [biography/dist/index.html](biography/dist/index.html)，先看整体地理旅程，再进入七幕人生、具体场景与同行人物。页面可离线阅读，每个场景附原书章节、PDF物理页与短引文。

设计方案见 [biography/DESIGN.md](biography/DESIGN.md)，重建与校验方式见 [biography/README.md](biography/README.md)。

## 重建阅读器

```powershell
python book_reader/scripts/build_reader_site.py
```

随后打开 `book_reader/site/dist/index.html`。本机原 PDF 为 `走出戈壁-单伟健.pdf`，不随 Git 提交。依赖、模型、下载缓存和临时文件均在 `.gitignore` 中排除。
