# OCR 本机环境记录

2026-09-22：旧试点已删除。以下仅保留全书处理工具的位置，供日后修订文字稿使用。

| 项目 | 路径及版本 |
| --- | --- |
| 专用 Python | `D:\WRK\走出戈壁-单伟建\.venv-ocr\Scripts\python.exe`（Python 3.11.9） |
| Python 库 | 虚拟环境内 `paddleocr==3.7.0`、`paddlepaddle==3.3.1`、`paddlex==3.7.2` |
| 模型原件 | `D:\WRK\走出戈壁-单伟建\models\paddleocr\official_models\PP-OCRv6_small_det\` 与 `PP-OCRv6_small_rec\` |
| 推理模型副本 | `%TEMP%\gobi-paddle-models\official_models\`；此前实际短路径为 `C:\Users\ALWAYS~1\AppData\Local\Temp\gobi-paddle-models\official_models\` |
| Tesseract | `C:\Program Files\Tesseract-OCR\tesseract.exe`，5.4.0.20240606 |
| Tesseract 语言文件 | `D:\WRK\走出戈壁-单伟建\models\tesseract\chi_tra.traineddata`、`eng.traineddata` |
| pip 缓存 | `D:\WRK\走出戈壁-单伟建\cache\pip\` |

Paddle 在本机读取含中文的模型路径时曾发生解析错误，因此推理用临时目录中的 ASCII 路径副本。若该副本被系统清理，应从模型原件恢复。全书 OCR 入口为 `scripts/run_ocr.py`，按页断点续跑；文字稿和阅读器不依赖旧试点目录。当前传记地图直接使用现有的分章文字稿，不需要重新 OCR。
