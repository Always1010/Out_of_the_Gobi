# 用 GitHub Runner 打包四份校订电子书

工作流：[Build corrected ebooks](https://github.com/Always1010/Out_of_the_Gobi/actions/workflows/build-ebooks.yml)。配置在 [build-ebooks.yml](../.github/workflows/build-ebooks.yml)。先把本次工作流改动合入 `main`，再对包含该工作流和校订稿的提交打标签。

## 打 Tag 触发

在仓库本地执行，示例版本号尚未使用时可直接采用：

```sh
git switch main
git pull --ff-only origin main
git tag -a book-v1.0.0 -m "校订电子书 v1.0.0"
git push origin book-v1.0.0
```

- 只有推送名称匹配 `book-v*` 的标签才自动构建；普通分支推送不触发。只在本地创建标签不会触发。
- Runner 检出**该标签指向的提交**，不是运行时最新的 `main`。请先合入工作流，再打标签；指向老提交的标签不会获得新工作流。
- 后续版本使用新标签，例如 `book-v1.0.1`。不要移动、删除或强制覆盖已发布标签，也不要一次推送大量标签。

## 下载、重跑和手动构建

1. 打开仓库 **Actions → Build corrected ebooks**，进入对应标签的成功运行。
2. 在运行摘要点下载链接，或在 **Artifacts** 下载 `gobi-ebooks-运行编号-尝试编号`。
3. 解压后包含：
   - `走出戈壁-简体.epub`
   - `走出戈壁-简体.pdf`
   - `走出戈壁-繁体.epub`
   - `走出戈壁-繁体.pdf`
   - `SHA256SUMS.txt`（四书的 SHA-256 校验值，不是第五份电子书）

下载需要登录有权读取仓库的 GitHub 账号。产物请求保留 90 天，以仓库实际保留策略为限，建议及时保存。过期后可重新构建。

同一提交需要重跑时，在原运行右上角选 **Re-run all jobs**，无需重新打标签。工作流合入默认分支后，也可点 **Run workflow**，选择要构建的分支手动运行；手动运行不创建标签。

工作流只上传 Actions 产物，不创建 GitHub Release、不推送提交、不替换根目录旧文件，也不需要配置额外密钥。如果以后需要长期公开下载，可另行增加 Release 发布步骤。

## 构建和校验范围

- GitHub 托管的 `ubuntu-24.04`，Python `3.12.14`，Python 包固定于 [requirements-build.txt](requirements-build.txt)；三个官方 Actions 均固定到完整 commit SHA。
- 从固定的 Noto CJK 官方提交下载完整字符集的 Noto Sans CJK SC/TC，校验 SHA-256 后生成 400 字重的 TrueType 字体。字体采用 [SIL Open Font License 1.1](https://github.com/notofonts/noto-cjk/blob/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/LICENSE)。兼顾原书中繁简混用的字形；不依赖 Windows 字体或 Runner 系统字体，缺字会使构建失败。
- 输入仅为仓库已有的校订分页稿、校改清单、OCR 核验数据和图片。不会运行 OCR，不需要原扫描 PDF，不重新进行 `tw2sp` 地区词汇转换，不使用根目录旧 EPUB/PDF。
- 重新生成连续稿、两份 EPUB、两份 PDF，以及用于综合检查的离线阅读器；**只上传四份电子书与校验值**。
- 校验既有 377 项已确认修正、239 项原文保留断言、源稿哈希和四份汇编；检查全书章节、卷首作者简介／献辞、版权页排除、图片、EPUB 内容、PDF 全文可搜索及连续页码。重建后源稿或证据发生变化也会失败。
- 这些自动检查不能替代全书逐字人工校勘。页数随字体排版变化，不要求与先前使用其他字体构建的 PDF 页数相同。
- 每次产物含生成时间等元数据，重跑的二进制 SHA-256 不保证相同；校验文件对应当次下载的四份成品。

## 本地复现（Linux）

在仓库根目录，用 Python 3.12.14 建立虚拟环境并安装固定依赖：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r book_reader/requirements-build.txt
python -m pip check
```

按工作流的 `Prepare verified Simplified and Traditional Chinese fonts` 步骤准备字体，将 `FONT_DIR`、`GOBI_FONT_SC`、`GOBI_FONT_TC` 设为本地可写目录和对应字体路径，再依次执行 `Rebuild from reviewed manuscripts and validate all four ebooks` 与 `Check deliverables and write SHA-256 checksums` 中的命令。输出在被 Git 忽略的 `book_reader/output/`；不要将下载缓存、字体或环境目录提交到仓库。

本次已在干净 Linux checkout 与独立虚拟环境中执行同一套构建／校验命令；GitHub Runner 的首次实际运行仍须在工作流合入并推送标签（或手动触发）后确认。运行失败时查看红色步骤日志，未通过校验不会上传成品。
