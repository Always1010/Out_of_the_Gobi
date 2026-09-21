# 简体连续书稿

`simplified-continuous/` 和 `traditional-continuous/` 是按章节整理的连续阅读版本。它们与原有的 `simplified/`、`traditional/` 并存，后两者保留 PDF 页锚点，便于回查扫描原书。

## 整理规则

- 删除章节内的 `<!-- PDF n -->` 页锚点。若一页末尾未结束句子，则直接与下一页首段拼接，不留下分页空行；原有段落结束处仍保留段落间距。
- 按原页顺序写入文字；该页含图片时，将图片注释放在该页文字之后。
- 原书的场景分隔符统一为 `★★★`。任何带 `★` 但不是标准三颗星的独立标记行，均视为 OCR 错误并改为 `★★★`；普通正文不作这一替换。
- 全页照片和照片拼版的 OCR 图注不写入正文，仅保留原书图片标记；图文混排的 PDF 9 保留正文，并删除已确认的照片图注。
- 简体稿使用大陆常用字形；除 OpenCC 转换外，已处理 `牠→它`、`衞→卫`、`簷→檐`、`敍→叙`、`擡→抬`。
- 保留章节标题、章节顺序和图片相对位置。

## 文件

- `simplified-continuous/`、`traditional-continuous/`：各 33 个独立章节。
- `book-simplified-continuous.md`、`book-traditional-continuous.md`：按相同顺序汇编的全书版本。

## 重新生成

在项目根目录运行：

```powershell
.\.venv-ocr\Scripts\python.exe book_reader\scripts\build_continuous_transcript.py
```
