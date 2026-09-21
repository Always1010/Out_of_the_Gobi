# 地图与书中照片

## 节点地图氛围插画（2026-09-22）

- 文件：`atlas-atmosphere.png`，1942 × 809。
- 工具：ImageGen；为本项目生成一次，未使用人物肖像或原书照片作生成参考。
- 画面：深蓝档案纸张、书页、戈壁芦苇与土屋、煤油灯；中部留白承载节点与路线。
- 用途：人生节点地图的低对比背景。属于艺术化场景，不是历史现场照片；页面明确标注。
- 真实人物和历史照片仍使用下列有出处的原始影像。

## 海陆轮廓

- 数据：Natural Earth，1:110m Land。
- 原始文件：`ne_110m_land.geojson`。
- 下载来源：https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson
- 数据说明：https://www.naturalearthdata.com/downloads/110m-physical-vectors/
- 许可：公共领域，见 https://www.naturalearthdata.com/about/terms-of-use/ 。
- 获取日期：2026-09-22。

此数据仅提供海陆轮廓，不表达行政边界。城市和湖区坐标仅为叙事定位；迁移线不是实际交通路线。

## 原书照片

使用已有 `book_reader/images/pages/` 中 PDF 第33、163、246、318、9、394、414页的整页照片。构建时按原样复制，不裁去原图注。照片属于原书内容，未获得独立公开转载许可；本项目作为本地阅读资料，不自动发布到外部网站。

原书事实、人物与引文来自原书简体文字稿及原书图注。书外续篇新增的文字来源记录在 `data/guide.json` 的 `sources` 中，每条均附支持的事实、来源类型和核查日期。

## 网络影像（2026-09-22新增）

以下三张图从作者官网获取，原样保存并已检查画面与标题对应。未修改、未生成替代肖像。

| 本地文件 | 内容 | 网页来源 |
| --- | --- | --- |
| `shan-portrait.jpg` | 单伟建肖像；拍摄时间未注明 | https://weijian-shan.com/biographyofweijianshan/ |
| `money-games.jpg` | 作者官网所示《Money Games》封面，含追加内容标记；文字出版年指2020年首版 | https://weijian-shan.com/books/ |
| `money-machine.jpg` | 《Money Machine》封面 | https://weijian-shan.com/books/ |

原始图片URL、来源、官网署名情况和备注保存在 `data/guide.json` 的 `images` 中。作者页未列明确摄影师、封面设计者或开放许可，不能视为已取得公开转载授权。本项目继续作为本地阅读材料，没有对外发布。网页显示作者官网来源链接，不把上传路径中的年份标为拍摄年份。
