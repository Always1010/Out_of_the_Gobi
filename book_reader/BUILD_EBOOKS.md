# GitHub Runner 打包并分别发布四份校订电子书

工作流：[Build corrected ebooks](https://github.com/Always1010/Out_of_the_Gobi/actions/workflows/build-ebooks.yml)。配置在 [build-ebooks.yml](../.github/workflows/build-ebooks.yml)。

## 已发布版本与手动补发

[book-v1.0 Release](https://github.com/Always1010/Out_of_the_Gobi/releases/tag/book-v1.0) 已由 [GitHub Runner 成功发布](https://github.com/Always1010/Out_of_the_Gobi/actions/runs/38091928739)，源码提交为 [0d55d703](https://github.com/Always1010/Out_of_the_Gobi/commit/0d55d703eb4fa34c7be24f6f8b3d2b5a3c2f723c)，包含诗句逗号和原书漏句号修订。四个独立文件已实际下载并通过 SHA-256 和全文校验。根目录旧成品已移除，后续通过 Release 分发。

需要为已有标签补发时：

1. 打开 **Actions → Build corrected ebooks → Run workflow**。
2. 分支选择 **main**，在 **release_tag** 输入已有标签，如 **book-v1.0**。
3. 点击 **Run workflow**；完成后打开对应 **Release**，四个电子书文件可分别下载。

这里使用 `main` 的最新工作流和发布程序，但**书稿、图片、Python 依赖清单及构建脚本严格取自所填标签指向的提交**；Runner 配置和字体准备规则由当前工作流固定。发布前再次检查标签仍指向该构建提交。不移动旧标签，不创建新标签，也不把最新 main 的书稿冒充旧标签版本。

不要点第一次旧运行的 **Re-run all jobs** 来升级流程；旧运行重跑仍使用当时的旧工作流。补发必须使用上面的新手动入口。启动时不存在的标签会失败；此流程只接受已有标签，不主动新建或移动标签。发布运行期间请勿由其他终端删除／移动同一标签。

## 后续新版本：打 Tag 自动构建并发布

先确保工作流和校订稿已在目标提交中，然后在仓库本地执行：

```sh
git switch main
git pull --ff-only origin main
git tag -a book-v1.0.1 -m "校订电子书 v1.0.1"
git push origin book-v1.0.1
```

- 推送 `book-v*` 标签触发构建并发布；使用 `book-v` 加数字开头的版本名，例如 `book-v1.0.1`、`book-v1.1.0-rc.1`，仅允许字母、数字、点、下划线、短横线。
- Runner 检出标签指向的提交。普通分支推送、只在本地创建标签都不会触发。
- 使用新版本标签，不移动、删除或强制覆盖旧标签。
- 手动运行时，`release_tag` **留空只构建 Actions 产物**；填写已有版本标签才发布该标签的 Release。此规则也适用于手动选择 tag 运行。

## 四个独立下载文件

Release 的 Assets 中分别提供：

- `out-of-the-gobi-zh-Hans.epub`：简体 EPUB
- `out-of-the-gobi-zh-Hans.pdf`：简体 PDF
- `out-of-the-gobi-zh-Hant.epub`：繁体 EPUB
- `out-of-the-gobi-zh-Hant.pdf`：繁体 PDF

下载文件名使用 ASCII，避免 GitHub 将中文名净化成 `-.epub`／`-.pdf`；上传时另设置中文显示标签。Actions 备份中的原文件名保持中文。

不把四份书合成一个 Release ZIP。GitHub 自动显示的 Source code ZIP／tar.gz 是源码归档，与四份电子书不同。

Actions 仍保留 `gobi-ebooks-运行编号-尝试编号` 作为备份，内含四书和 `SHA256SUMS.txt`。下载 Actions 产物需登录，产物请求保留 90 天，以仓库策略为限；Release 文件不受 Actions 产物到期时间影响。校验值也保存在发布说明的构建记录中。

## 安全重跑与发布失败

- 新 Release 先创建草稿，四个文件全部上传并验证 GitHub 返回的 SHA-256 后才公开发布。
- 普通构建任务只有 `contents: read`；独立发布任务才有 `contents: write`。不需要额外密钥或修改仓库权限设置。
- 发布任务运行当前工作流提交中的受控发布程序，不运行旧 Tag 中的书稿构建代码；文件通过本次构建的精确 artifact ID 传递。
- 失败后可重跑新流程的失败任务。已验证、来自同一源码提交的文件会保留，仅补齐缺失文件；重建时间变化不会强制替换已有文件。
- 早期失败草稿中被净化成 `-.epub`／`-.pdf` 的资产，只有在源码提交一致、SHA-256 唯一匹配本流程记录时才原位重命名为正确英文名，保留原 asset ID 和内容，不删除、不重新上传。未知或同名冲突资产仍会停止。
- 不删除或覆盖同名资产，不改动无关资产，不发布用户原有的无关草稿。遇到未知同名文件、校验不匹配、标签被移动等情况会停止，并在日志说明原因。
- 若出现 `Existing release records a different source commit`，说明该标签已有 Release／草稿记录了另一份源码；删除 Actions 运行或删除重打 Tag 不会删除 Release。先在仓库 **Releases** 核对对应草稿及其构建源提交；若确认只是应废弃的失败草稿，由维护者删除该草稿后，再对使用新流程的运行选择 **Re-run failed jobs**。已公开的版本应另用新版本标签，避免替换已交付内容。
- GitHub 偶尔会在失败上传后留下零字节 `starter` 资产；自动重跑不会删除它，会安全停止。需要人工确认并清理该失败资产后再重跑，不要删除已成功的文件。
- 补齐已有公开 Release 时保留原有说明，并追加本流程的构建记录。不会把旧版本强行设为仓库最新 Release。
- 已启用不可变发布的 Release 无法追加缺失文件；流程会停止而不改动它，需要另用新版本标签。
- 如果整个构建重跑，PDF／EPUB 生成时间等元数据可变化，因此二进制校验值不保证与上次相同；同一标签已成功发布的文件保持原样。

## 构建和校验

- GitHub 托管 `ubuntu-24.04`，Python `3.12.14`；Python 包固定于 [requirements-build.txt](requirements-build.txt)，官方 Actions 固定到完整 commit SHA。
- 固定 Noto CJK 官方字体提交，下载 Sans 与 Serif 两套 SC／TC TrueType 字体，校验 SHA-256 并固定 400 字重；另固定 LXGW WenKai Light v1.522（300字重）及校验值用于引言；覆盖原书混用字形，无须 Windows 字体。字体许可：[SIL OFL 1.1](https://github.com/notofonts/noto-cjk/blob/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/LICENSE)。
- 仅使用仓库校订稿、校改清单、核验 OCR 数据和图片，不运行 OCR，不需要原扫描 PDF，不重新执行 `tw2sp`，不使用根目录旧 EPUB／PDF。
- 校验 378 项已确认修正、238 项原文保留断言、源稿哈希、全书汇编、章节、卷首、版权页排除、图片、EPUB 内容及 PDF 全文和连续页码。重建导致源稿变化会失败。
- 同时重建离线阅读器供综合检查，但发布内容仅为四份电子书。这些检查不替代全书逐字人工校勘。
- `book-v1.0` 已通过真实 GitHub Runner 构建与 Release 发布；四个下载文件的 SHA-256 与服务端记录一致，简繁 EPUB／PDF 全文、卷首、图片、图注与连续页码检查通过。

## 本地复现

在仓库根目录使用 Python 3.12.14：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r book_reader/requirements-build.txt
python -m pip check
python -m unittest discover -s book_reader/tests -p 'test_publish_release.py' -v
```

按工作流准备字体，可用 `GOBI_FONT_DIR=cache/build-fonts` 指定统一字体目录，或设置 `GOBI_FONT_SC/TC`、`GOBI_SERIF_SC/TC`、`GOBI_LEADIN_SC/TC` 分别指定文件；工作流的 `FONT_DIR` 是准备步骤使用的目录变量，再执行构建和校验步骤。生成文件在被 Git 忽略的 `book_reader/output/`，不要提交字体、下载缓存或虚拟环境。发布测试不会联网或创建真实 Release。

## 新版版式构建

新版源码增加作者简介正文、独立图版页、自序末肖像、双字体带章号目录、原书引言与11处诗词分行。上述改变在新Tag中发布，不移动或覆盖已发布 `book-v1.0`。高清四书仍是正式构建产物；可选 `build_review_pdf.py --script simplified` 只生成便于附件审阅的220dpi图片副本，不改变发布文件。

新增单元测试、语义边界断言、图文分离及诗行全量验证与既有校勘断言一起运行。字体缺字或未找到精确字体时构建失败，不回退到混淆章号、标题与引言的统一字体。
