# 简体连续书稿

`simplified-continuous/` 是按章节整理的连续阅读版本。它与原有的
`simplified/` 并存，后者保留 PDF 页锚点，便于回查扫描原书。

## 整理规则

- 删除章节内的 `<!-- PDF n -->` 页锚点，使跨页句子连续排版。
- 按原页顺序写入文字；该页含图片时，将图片注释放在该页文字之后。
- 原书的场景分隔符统一为 `★★★`。任何带 `★` 但不是标准三颗星的独立标记行，均视为 OCR 错误并改为 `★★★`；普通正文不作这一替换。
- 保留章节标题、章节顺序和图片相对位置。

## 文件

- `simplified-continuous/`：33 个独立章节。
- `book-simplified-continuous.md`：按相同顺序汇编的全书版本。

## 重新生成

在项目根目录运行：

```powershell
.\.venv-ocr\Scripts\python.exe book_reader\scripts\build_continuous_transcript.py
```
