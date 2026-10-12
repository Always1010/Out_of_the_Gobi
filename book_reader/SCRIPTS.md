# 脚本入口与路径约定

所有示例从仓库根目录运行，先激活 Python 环境并准备字体；不需要特定盘符、用户名或机器目录。

## 常用入口

| 工具 | 用途 / 输入 → 输出 |
| --- | --- |
| `scripts/build_pages_site.py` | 首页模板与已提交连续稿/图片 → `_site/`；由 Pages 工作流部署 |
| `scripts/build_reader_site.py` | 连续稿/图片/字体 → `site/dist/`；`--output-dir` 可改位置，`--online` 生成在线版 |
| `scripts/build_continuous_transcript.py` | 已校订分页稿 → 连续稿和整书汇编；不会重新 OCR |
| `scripts/build_epub.py`、`scripts/build_pdf.py` | 连续稿/版式/图片/字体 → `output/` 简繁电子书 |
| `scripts/build_review_pdf.py` | 已生成 PDF → 独立审阅副本及文件名/哈希报告；不覆盖原件 |
| `scripts/proofreading.py` | 按精确校改清单重放补丁；修改源稿前检查匹配条件 |
| `scripts/validate_proofreading.py` | 校订哈希、补丁和派生稿一致性检查 |
| `scripts/validate_manuscript.py` | 结构/章节/源 OCR 验证；`--exports` 加验四书与离线阅读器 |
| `scripts/validate_paths.py` | 跟踪文本/归档资源的路径回归检查；用法见 `--help` |
| `scripts/publish_release.py` | 有网络写入的正式 Release 发布；与本地构建分开 |
| `scripts/prepare_reader_fonts.py` | 下载并核验简体阅读器字体到指定缓存目录；不安装系统字体 |

`export_common.py`（内容/版式及派生裁图）、`book_fonts.py`（字体定位与子集）、`ocr_common.py`（OCR读取与纯转换函数）是共享模块，不是需要逐个执行的流水线。历史采集/组稿工具和联系表见 [archive/README.md](archive/README.md)。

## 输入与路径

- 项目内资源从脚本位置计算仓库根，再拼接相对路径；输出目录不得写死某台电脑的位置。
- 字体可以集中放在 `cache/build-fonts/` 并设置 `GOBI_FONT_DIR=cache/build-fonts`；也可分别设置 `GOBI_FONT_SC/TC`、`GOBI_SERIF_SC/TC`、`GOBI_LEADIN_SC/TC`。字体必须匹配指定家族和字重，缺字体会停止，不静默替换。显式角色文件优先，随后查配置目录/角色文件同目录和仓库 fonts。
- 原扫描是可选外部输入：离线阅读器可用 `--source-pdf <源PDF>` 或 `GOBI_SOURCE_PDF`；未提供/不存在时隐藏原页按钮。自定义输出位置生成相对链接，在线模式始终返回首页。Windows跨盘无法生成相对链接时明确报错，应把原扫描和阅读器放在同一盘。
- 运行时由参数、环境变量和平台接口解析绝对路径是正常的；源码、公开文档及持久化记录不应写死本机路径。CI 的 `runner.temp` 保留动态定位语义。
- JSON是业务数据，不按扩展名批量清除。420份 OCR 证据、校改清单、章节/卷首/引言/诗行/落款清单和图片配置均保留。原OCR的 `input_path` 仅记录逻辑图片名。
- 不提交生成书、字体、模型、虚拟环境和缓存；清理 output 前先保存需要的交付成果，不删除外部原扫描。

## 2026-10-12 整理记录

本次拆出 `ocr_common`，归档4个历史采集/组稿工具、35张联系表及2份旧文档；移除旧根目录成品复制工具；421份OCR索引/逐页文本派生文件改为按需再生。420份原OCR仅净化输入路径，其文本、坐标、分数和元信息保持不变。字体及外部PDF/模型/缓存配置化，离线原页入口与审阅报告不再固化机器位置。增加路径回归和相关测试，并接入两条CI构建链路。书稿、源图与校改依据不因目录整理改写。

历史标签兼容：手动明确指定旧标签补发、且该标签早于路径检查器时，电子书工作流会警告并跳过新检查器；不改历史源码。普通构建/新标签缺少检查器视为错误，Pages始终执行检查。
