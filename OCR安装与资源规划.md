# 《走出戈壁》前 20 页试点：OCR 安装与资源实测

记录日期：2026-09-21。以下为**本机实际安装和前 20 页实测**，而非预估。

## 工具性质

| 工具 | 安装形态 | 本次用途 |
| --- | --- | --- |
| PaddleOCR 3.7.0 + PaddlePaddle 3.3.1 | 项目专用 Python 虚拟环境中的库与 CPU 推理依赖；调用 PP-OCRv6 small 检测及识别模型 | 20 页主 OCR |
| Tesseract 5.4.0.20240606 | Windows 原生命令行程序，另配 `chi_tra`、`eng` 语言数据 | 6 页对照 OCR |

两者的文件下载完成后可在本机离线处理，不按页调用云端 OCR。交互图谱浏览时不需要运行 OCR，也不需要启动 Python。**PP-OCRv6 medium 未安装、未测试**：small 在抽样正文上已达到试点可用水平；后续若遇到低质量页面再考虑 medium。

## 本机条件

| 项目 | 检查结果 |
| --- | --- |
| CPU | AMD Ryzen 7 4800U，16 个逻辑处理器；本次只用 CPU，Paddle 限 4 线程 |
| 内存 | 物理内存约 15.4 GiB；安装前检查时可用约 5.9 GiB |
| GPU | AMD Radeon 集成显卡；未用于推理 |
| 原始 PDF | `D:\WRK\走出戈壁-单伟建\走出戈壁-单伟健.pdf`，420 个物理页，约 48 MB；抽查扫描页约 4306×6080 像素 |
| Python | `D:\Python311\python.exe`，3.11.9；由此创建项目虚拟环境 |
| 磁盘 | 本次结束检查：D: 可用约 53.8 GB，C: 可用约 22.5 GB；两次空闲容量读数包含其他程序活动，不能精确归因于本项目 |

## 实际安装路径

| 内容 | 实际路径 | 当前体量 |
| --- | --- | ---: |
| Python 虚拟环境，包括 `paddleocr`、`paddlepaddle`、`paddlex` | `D:\WRK\走出戈壁-单伟建\.venv-ocr\` | 845.9 MiB |
| PP-OCRv6 small 检测及识别模型原件 | `D:\WRK\走出戈壁-单伟建\models\paddleocr\official_models\PP-OCRv6_small_det\` 和 `PP-OCRv6_small_rec\` | 合计 30.1 MiB |
| Paddle 可运行的 ASCII 路径模型副本 | `C:\Users\ALWAYS~1\AppData\Local\Temp\gobi-paddle-models\official_models\` | 30.1 MiB |
| Tesseract 程序 | `C:\Program Files\Tesseract-OCR\tesseract.exe` | 程序目录约 237.9 MiB |
| 繁体中文、英文语言数据 | `D:\WRK\走出戈壁-单伟建\models\tesseract\chi_tra.traineddata` 和 `eng.traineddata` | 合计 16.3 MiB |
| pip 下载缓存 | `D:\WRK\走出戈壁-单伟建\cache\pip\` | 217.9 MiB |
| OCR、扫描页图像与图谱试点 | `D:\WRK\走出戈壁-单伟建\pilot20\` | 约 6.3 MiB（记录时） |

Tesseract 安装器未采用拟定的 D 盘程序位置，最终装在 `C:\Program Files`。Paddle 推理组件在本机读取含中文的模型目录时出现解析错误，所以在系统临时目录保留一份 **ASCII 路径**模型副本；这不是第二套模型。未来若临时目录被清理，需要从 D 盘原件重新复制，并设定 `PADDLE_PDX_CACHE_HOME` 指向该临时目录。运行记录中的临时目录短路径需按本机实际 `%TEMP%` 确认。

## 前 20 页实测

原 PDF 为扫描影印版，无可用文字层。本次以 300 dpi 灰度页图做 OCR；页图保留在 `pilot20\tmp`，供图谱显示原页。试点单进程顺序执行。

| 指标 | PaddleOCR PP-OCRv6 small | Tesseract 繁体 + 英文 |
| --- | ---: | ---: |
| 处理页 | PDF 1–20，共 20 页 | PDF 6、8、10、15、19、20，共 6 页 |
| 平均每页耗时 | 18.6 秒 | 5.1 秒 |
| 总耗时 | 371.1 秒 | 约 30.4 秒 |
| 进程观测最高 RSS | 847.2 MiB | 180.9 MiB |
| 两段人工校对正文（共 547 字）编辑差异 | 3 处，0.55% | 10 处，1.83% |

抽样字符错误率经过 Unicode NFKC、去空白处理，计算的是两个**人工核对片段**，不是全页或全书准确率。Paddle 在第 6 页目录读到内容，Tesseract 对该页输出空白；目录、照片、手写题字仍需单独检查。第 14、18 页为空白页。OCR 共输出 7,911 个字符，包含页码和少量图片误识别文字。

本机推理峰值内存低于先前按 2–5 GiB 留出的保守预算。完整 420 页若沿用此次平均耗时，纯 OCR 约需 2.2 小时；这是简单线性估算，未计失败重跑、校对与抽取图谱的时间。建议逐页断点续跑、每页保留 OCR JSON，并优先对专名、日期和关系做人工核验。

## 复现入口

```powershell
Set-Location 'D:\WRK\走出戈壁-单伟建'
$env:PADDLE_PDX_CACHE_HOME = Join-Path $env:TEMP 'gobi-paddle-models'
$env:HF_HOME = $env:PADDLE_PDX_CACHE_HOME
.\.venv-ocr\Scripts\python.exe -X utf8 pilot20\run_paddle.py 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
.\.venv-ocr\Scripts\python.exe -X utf8 pilot20\build_text.py
.\.venv-ocr\Scripts\python.exe -X utf8 pilot20\build_graph.py
.\.venv-ocr\Scripts\python.exe -X utf8 pilot20\build_site.py
```

上述命令假设 `pilot20\tmp\page-001.png` 等 300 dpi 页图已存在，且临时模型副本仍在 `%TEMP%\gobi-paddle-models\official_models\`。如副本丢失，可从 D 盘的 `models\paddleocr\official_models\` 复制过去。Tesseract 对照可用 `pilot20\run_tesseract.py`，抽样校对用 `pilot20\evaluate_ocr.py`。

## 官方资料

- [PaddleOCR OCR 管线文档](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html)
- [PP-OCRv6 模型说明](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv6/PP-OCRv6.html)
- [Tesseract 繁体中文语言数据](https://github.com/tesseract-ocr/tessdata_best/blob/main/chi_tra.traineddata)
