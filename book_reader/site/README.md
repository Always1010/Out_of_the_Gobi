# 本地离线阅读器

运行 `..\\scripts\\build_reader_site.py` 后，直接用浏览器打开 `dist\\index.html`。

页面按目录一次显示一节，正文取自 `text/simplified-continuous/`，没有扫描 PDF 的分页空行；原书图片保留在相应章节，点击可放大。目录在电脑上位于左侧，在手机上横向滑动，能直接看到章名。它不需要联网或启动服务。

源稿修改后，重新运行生成脚本即可更新 `dist/` 中的离线网页。
