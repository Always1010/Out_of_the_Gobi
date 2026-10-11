# 《走出戈壁》简体文字稿与离线阅读网页

本目录用于全书 OCR、简体文字稿、原书图片及阅读网页。原始 PDF 保留在上级目录 `../走出戈壁-单伟健.pdf`，不在此复制。逐页 OCR 已独立保存在本目录中；本机工具路径见 [OCR 环境记录](OCR环境.md)。

## 目标与交付

- 覆盖原 PDF 的全部 420 个物理页，记录每页的处理状态，并分别保存 PDF 页码与印刷页码。
- 先保留逐页 OCR 原始结果，再整理成按章分文件的 UTF-8 繁体 Markdown；分别保存经核对的繁简分页稿，再由分页稿生成连续稿和全书汇编，避免地区词库改写原词。
- 登记并保存照片、插图、图表、手写内容和整页图片，按原书位置放入网页。图片本身的繁体字不强制转换。
- 生成可本地离线阅读的静态网页：目录、全文搜索、字体和主题设置、阅读进度、图片放大、跳转 PDF 原页。
- 完整性验收记录放在 `qa/`：420 页覆盖、章节边界、图片清单、抽样文字校对及网页检查。

## 目录约定

| 目录 | 用途 |
| --- | --- |
| `scripts/` | 可重复运行的 OCR、整理、简繁转换及网页生成脚本 |
| `ocr/` | 逐页原始识别文本、坐标和置信度，以及页索引 |
| `text/` | 按章整理的繁体和简体 Markdown、章节索引、全书纯文本 |
| `images/` | 从扫描页裁出的网页图片及图片清单 |
| `site/` | 本地离线阅读网页 |
| `qa/` | 覆盖清单、疑难页和验收结果 |

所有生成物应可通过脚本从原 PDF、OCR 输出和经校对的文字稿重建。临时逐页渲染图不作为最终交付，避免额外保存 420 张高清扫描图。

## 执行顺序

1. **页索引**：核对目录、前后内容和页码映射，检查已保存的逐页 OCR 结果。
2. **全书 OCR**：使用本机 PaddleOCR 分批识别，逐页落盘并支持断点续跑；记录空白、图片页和失败页。
3. **图片清点**：本机生成每张约 12 页的总览图（420 页约 35 张）；结合 OCR 文本密度、版面信息和视觉检查登记候选页。对候选页查看原尺寸，裁切图片并核对说明。不能将 OCR 字少直接判为空白页。
4. **章节整理与简体转换**：恢复标题、段落、跨页句和图注；校对专名、数字及疑难页；保留繁体稿，将简体稿作为派生版本。
5. **网页生成**：以简体稿和图片清单生成静态阅读站；首屏进入正文阅读，图片按原位置出现，并提供 PDF 原页链接。
6. **验收**：逐页检查覆盖状态，核对每张已登记图片的位置，检查搜索、阅读进度、离线使用和手机排版。

## 模型分工与用量控制

**推荐主任务：GPT-5.6 Terra，中等推理。**章节结构整理、转换规则、阅读网页实现和常规校验需要持续判断，但无需全程使用 Sol 高推理。OCR 主计算由本机 PaddleOCR 完成，不让语言模型逐页重做 OCR。

**一个图片清点 Sub-agent：GPT-5.6 Luna，低推理。**主 Agent 先生成总览图；Sub-agent 分批标注图片候选页与不确定页，只提交结构化清单，不编辑最终文字或网页。该任务可与本机 OCR 并行。先用包含已知照片的试点页检验它的漏检情况；如果漏检，缩小总览图的拼页数或把疑难页升至 Terra 复核。

**GPT-5.6 Sol：仅用于疑难问题。**例如复杂图文混排、章节边界争议、棘手的 OCR 纠错或网页实现受阻。高推理级别不作为整项任务默认设置。

主 Agent 整合 Sub-agent 的清单，并复核全部候选页、不确定页以及无图页抽样。整书图片是否齐全由页清单和最终验收判断，不能只依赖低成本模型的一次分类。

模型定位和 Codex 用量参考：[Codex 定价与模型说明](https://learn.chatgpt.com/docs/pricing)、[OpenAI 模型目录](https://developers.openai.com/api/docs/models)。实际消耗还受上下文、图片、工具调用和重试影响；官方给出的本地消息数量是范围估计，不是本项目的固定费用。

## 当前状态

- 420 个物理页的 OCR 结果和逐页索引已生成，文字稿已完成校对与修订。
- 已整理 33 个章节或前后附录，补回作者简介与献辞两节卷首；繁简分页版、连续版及全书汇编同步。网页使用简体连续版，既有章节 ID 保持不变。
- 已登记、保存 22 个封面／题字／正文图片页，并在 `images/captions.json` 整理 16 页可辨图注；新增两张卷首原图单列于 `images/frontmatter/`。扫描第350页照片及三条图注已恢复；第352页仍为第二十六章正文。
- 离线阅读网页位于 `site/dist/index.html`，可由 `scripts/build_reader_site.py` 重建。最新修改与保留疑点见[本次修改说明](qa/本次修改说明.md)和[原文疑点说明](qa/原文疑点说明.md)。

## EPUB 阅读版

运行 `..\.venv-ocr\Scripts\python.exe scripts\build_epub.py`，可从简繁连续稿生成两套 EPUB 3 文件，保存到 `output/`。该目录是被 Git 忽略的生成目录；正式下载文件发布到 [GitHub Releases](https://github.com/Always1010/Out_of_the_Gobi/releases)，不再将成品书提交到仓库根目录。电子书包含 33 节正文及前后附录、作者简介与献辞、原书封面和题字页、20 处正文图片以及已核对的图注，并提供可跳转目录。

文字稿已完成校对与修订，整理版仍可能存在错字、漏字、标点、排版或图片标注偏差。发现问题时，请在项目 Issues 中注明文件名、章节、问题片段和建议更正。

## 文字重排 PDF

运行 `python scripts\build_pdf.py`，可生成简体和繁体两套 B5 版式 PDF，同样保存到 `output/`。运行环境需有 ReportLab、Pillow 和 OpenCC。正文与章号使用 Noto Sans SC/TC，章标题使用 Noto Serif SC/TC，章首引言使用 LXGW WenKai Light；三类字体均实际嵌入，缺少字体或字形即停止，不静默替换。可通过 `GOBI_FONT_SC/TC`、`GOBI_SERIF_SC/TC`、`GOBI_LEADIN_SC/TC` 指定字体；官方固定版本、SHA-256 和静态字重实例化见 `.github/workflows/build-ebooks.yml`。简体图注仅作字形转换，避免地区词库替换原词。PDF 有可搜索的正文、目录页、章节书签和页码。原始 420 页扫描 PDF 仍单独保留，不会被覆盖。

## 本次原扫描回改

[book-v1.0 Release](https://github.com/Always1010/Out_of_the_Gobi/releases/tag/book-v1.0) 已发布四个独立文件，包含诗句逗号与原书漏句号修订；实际下载文件的 SHA-256、正文、卷首、图片与连续页码检查均通过。根目录四份旧 EPUB/PDF 已移除，校订源稿与全部构建程序保留。[GitHub Actions Tag 打包与发布](BUILD_EBOOKS.md) 用于后续新版本和已有标签补发。

修改范围和保留疑点分别见 [本次修改说明](qa/本次修改说明.md)、[原文疑点说明](qa/原文疑点说明.md)。版权与版本信息页依本次裁决不收入阅读版；阅读 PDF 从第一页起连续编号。

日常从已校对分页稿重建：

```sh
python book_reader/scripts/build_continuous_transcript.py
python book_reader/scripts/build_epub.py
python book_reader/scripts/build_pdf.py
python book_reader/scripts/build_reader_site.py
python book_reader/scripts/validate_manuscript.py --exports
python book_reader/scripts/validate_proofreading.py
```

以上命令从仓库根目录执行，成品留在被 Git 忽略的 `book_reader/output/`。历史本地复制工具 `publish_ebooks.py` 仍保留，但 Release 发布和日常重建不需要运行它。需要重新从 OCR 组稿时先运行 `assemble_transcript.py`；脚本会自动重放 `qa/proofreading-corrections.json` 中的逐页精确修正，再按上述顺序重建。原始 OCR 不改写；位置与预期不符会停止，避免静默丢失校改。

## 阅读版版式与诗歌

- 作者简介的七段转写已存在，原导出却以扫描图为可见主体。现改为真正可见、可检索的正文；献辞继续保留原图。
- 20处正文图版各占一页，电子图注随对应图版；跨页拼版图注显式分配，自序肖像移至全部自序和日期之后。前言图片仅提取肖像阅读区域，扫描证据原图不动。
- 29章目录补齐中文章号，章号用无衬线字体、标题用衬线字体；开场白与29章的37段引言依原扫描边界以较细、略小的楷体呈现。
- 原扫描全书清点得到11处独立诗词/歌词、81行，依 `text/verse-layout.json` 精确分行：整块内缩两字、每行左齐、首行不再额外缩进。普通行内引句不变。简繁分别匹配已校稿，任何字符偏移或多次匹配都会停止。
- `text/lead-ins.json`、`text/verse-layout.json`、`text/signature-layout.json` 和 `images/reading-layout.json` 是可审计的版式边界清单；分页源稿继续保留原扫描页码与校改哈希，不因排版重写原文。三类导出共用同一语义数据。
- EPUB 的图版分页声明由阅读器执行，重排字号、屏幕和阅读器可影响分页；PDF 的独立图版页固定。离线网页按阅读模式显示图版，不承诺与PDF同页数。

完整高清PDF之外，可生成文字、字体、链接、书签与版式不变的较小审阅副本：

```sh
python book_reader/scripts/build_review_pdf.py --script simplified
python -m unittest discover -s book_reader/tests -v
```

审阅副本仅对有效分辨率较高的图片按220dpi/JPEG91生成，原图与高清母版保留。逐页文本和位置、字体程序、书签、链接自动比对结果写入同名 `.review.json`。版式复核见 [阅读版版式验收](qa/reading-layout-review.md)。本次新稿不覆盖已发布 `book-v1.0`；发布新版需另行使用新版本Tag。

前言与自序的实际署名、职衔、日期改为成组右对齐，简繁与三类阅读输出一致。正文中的书信日期描述、日记日期与普通人名不自动当成落款；全书核查范围及判断见现有[本次修改说明](qa/本次修改说明.md)。
