# 历史采集与复核归档

这里保留有参考价值的原扫描采集/初稿重建工具，不是日常打包的前置步骤。旧机器目录已从源码和说明移除；当前入口见 [脚本说明](../SCRIPTS.md)。

## 工具与风险

| 工具 | 用途 / 前提 |
| --- | --- |
| `scripts/run_ocr.py` | PaddleOCR识别；或无需PDF、模型和Paddle环境导出现存JSON的文本/索引 |
| `scripts/render_image_pages.py` | 从外部PDF重新提取清单中的图片，会覆盖图片与清单 |
| `scripts/build_contact_sheets.py` | 外部PDF → `archive/contact_sheets/` 的35张全书联系表 |
| `scripts/assemble_transcript.py` | 从420份OCR重组分页稿；**会先删除重建简繁分页目录**并重放记录的补丁，未记录的人工改动可能丢失；不要日常运行 |

正常电子书验证仍读取 `ocr/paddle_small/`，不能删除该目录。共享函数已移至 `scripts/ocr_common.py`，正常构建不再导入归档组稿入口。

## 只恢复逐页文本与索引（不需要原PDF）

```sh
python book_reader/archive/scripts/run_ocr.py --export-only
```

默认输出 `book_reader/output/ocr/pages.json` 与 `pages/*.txt`；用 `--output tmp/ocr-export` 改位置。它们是可再生副本，不再纳入Git，原始JSON不变。

## 明确需要重新采集时

以下使用占位输入；把 `<源PDF>` 换成自己的文件位置，不要把机器位置提交进文档。

```sh
python book_reader/archive/scripts/run_ocr.py --pdf '<源PDF>' --pages 1-20
python book_reader/archive/scripts/render_image_pages.py --pdf '<源PDF>'
python book_reader/archive/scripts/build_contact_sheets.py --pdf '<源PDF>'
```

三个工具支持 `GOBI_SOURCE_PDF`；未配置时仅为兼容旧用法尝试仓库根的 `走出戈壁-单伟健.pdf`，该文件不在Git中。此历史文件名不随作者名自动更改。

OCR额外支持：
- `--cache-dir` / `GOBI_OCR_CACHE_DIR`：模型缓存；未显式配置时尊重 `PADDLE_PDX_CACHE_HOME` 与 `HF_HOME`，否则使用系统临时缓存。
- `--temp-dir` / `GOBI_TEMP_DIR`：临时页目录。
- `--det-model-dir` / `GOBI_OCR_DET_MODEL_DIR`、`--rec-model-dir` / `GOBI_OCR_REC_MODEL_DIR`：外部模型目录。
- `--force`：重新识别指定页面，会改写原始证据，应仅在明确需要时使用。

扫描渲染依赖 PATH 内的 `pdftoppm`；图像工具需 Pillow；真正识别还需另备 PaddleOCR/Paddle及模型。正常构建requirements不是完整OCR环境。旧版本信息见 [OCR环境](docs/OCR环境.md)。

[全书复核快照](docs/full-manuscript-review.md) 是2026-09-22记录，保留原验收范围和限制，不冒充当前图片计数或验收状态。联系表是目视复核参考，不被当前电子书/Pages构建读取。
