# V2EX 短贴（直接复制粘贴）

**标题**：接入麦当劳 MCP 踩了 3 个坑，官方文档一个都没写

**正文**：

参加麦当劳 MCP 创意赛做个 Skill，接 API 时发现三个坑，官方 README 里完全没写，按文档写必失败：

**1. `query-nearby-stores` 要 city + keyword 一起传**
- 只给 city → `600050 收藏餐厅列表为空`
- 只给 keyword → `600058 城市名或者关键词不能为空`
- 而且 inputSchema 的 properties 里压根没有 `latitude/longitude` 入参，我第一版自造了经纬度，纯属 wasted

**2. `query-meals` 不返回商品名，也不返回价格**
只有 `{"code":"9900004064","tags":["爆款"]}`。想报价必须再调 `calculate-price`，商品名也从那里反查。

**3. `calculate-price` 的单位是「分」**
返回 `price=3450` → 34.50 元。而`order-list` 返回的`realTotalAmount` 是元的字符串 `"15.5"`，**两者方向相反**，混用就是数量级错误。

补充两个：
- `order-list` 不接受任何参数，传参反而校验失败
- 历史订单混着「整单退款」，不过滤会让月度支出虚高

**还有**：`list-nutrition-foods` 不含咖啡因字段，所以任何「AI 控制咖啡因」的数据只能来自本地基准表——那就得诚实标注，不能假装是实时数据。

把三个坑全固化成代码里的运行时断言 + 24 个回归测试，验证脚本也开源了，任何人能自己复现：

https://github.com/lilyco-42/mcd-nightfuel

参赛作品（欢迎看看其他参赛者的思路）：
https://github.com/M-China/mcd-developer-innovation-challenge/issues/505

---

发布提示：V2EX 发帖选「酷工作/分享」或「程序员」节点，**别选「推广」**（会被折叠，V2EX 用户反感硬广）。带 star 请求的话用上面的软性表述，别写「求 star」。