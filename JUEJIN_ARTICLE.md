# 掘金长文（可直接粘贴发布）

> 建议标签：`MCP` `AI` `开源项目` `LLM` `程序员`
> 建议封面：README 顶部那张终端录屏的截图

---

# 接入麦当劳 MCP 踩了 3 个坑，官方文档一个都没写

上周接了麦当劳官方的 MCP Server（`https://mcp.mcd.cn`），想做一个夜班场景的 Skill 参赛。

接完之后最大的感受不是「AI 不好用」，而是——**官方文档能让你跑通 happy path，但一遇到真实场景就处处碰壁**。

官方 README 我读了三遍，跑通了基础调用，然后开始逐个 Tool 试真实参数，才发现三个坑：**任何一个都能让新手直接卡死，而且文档里完全没有提。**

我把踩坑过程和验证脚本都开源了（文末有链接），这里把结论先说清楚。

---

## 坑一：门店查询要city 和 keyword 一起给，缺一个都报错

`query-nearby-stores` 是所有链路的起点——不知道哪家店，后面查菜单、查券、核价全都无从谈起。

它的 `inputSchema.required` 写着两个必填：

```json
["beType", "searchType"]
```

看起来只要传 `beType` 和 `searchType` 就行了对吧？

**错。**

我第一次调用是这样：

```json
{
  "latitude": 31.2304,
  "longitude": 121.4737,
  "searchType": 2,
  "beType": 1
}
```

报错：

```json
{"success":false,"code":600058,"message":"城市名或者关键词不能为空"}
```

注意关键词 **`城市名或者关键词`** —— 服务端在找 city 或 keyword，但我压根没传这两个字段。

那我寻思，把经纬度去掉，传个 `city` 总行了吧：

```json
{"city": "上海", "searchType": 2, "beType": 1}
```

换个错误码：

```json
{"success":false,"code":600050,"message":"收藏餐厅列表为空，请您提供城市+关键词进行搜索"}
```

这次city 传了，报错却说「**城市+关键词**」。

反复试了几轮才摸清规律：**`city` 和 `keyword` 必须同时提供，缺一个都不行。**

- 缺 `keyword` → `600058 城市名或者关键词不能为空`
- 缺 `city` → `600050 收藏餐厅列表为空，请您提供城市+关键词进行搜索`

正确的调用：

```json
{
  "city": "上海",
  "keyword": "徐家汇",
  "searchType": 2,
  "beType": 1
}
```

返回：

```json
{
  "success": true,
  "data": [{
    "storeCode": "1450323",
    "storeName": "麦当劳上海徐汇漕溪北路百脑汇餐厅",
    "address": "漕溪北路339号",
    "distance": 121
  }]
}
```

**还有一个更隐蔽的坑**：我最初是看了 `inputSchema` 的 `properties` 才写的代码，发现里面只有 `beType` / `city` / `keyword` / `searchType`——**根本没有 `latitude` / `longitude` 这两个字段**。

也就是说，定位这件事完全由服务端根据 city + keyword 去做，客户端不需要（也不应该）传经纬度。我第一版代码里那个 `latitude/longitude` 参数，是纯粹的臆想出来的。

> 教训：**inputSchema 的 properties 才是真实契约**。文档正文里的举例参数很可能是示意性的，不能直接照抄。

---

## 坑二：菜单接口不返回商品名，也不返回价格

拿到 `storeCode` 之后，下一步是查这个店在卖什么：

```json
{"storeCode": "1450323", "orderType": 1, "beType": 1}
```

调用成功，返回了菜单。但结构是这样的：

```json
{
  "categories": [{
    "name": "人气热卖",
    "meals": [
      {"code": "9900016076", "tags": ["心形薯饼同款比心"]},
      {"code": "9900004064", "tags": ["爆款"]},
      {"code": "521950", "tags": ["蓝莓"]}
    ]
  }]
}
```

盯着看了几秒，我意识到两件事：

**1. 没有商品名。** 只有 `code` 和 `tags`。

**2. 没有价格。** 一个数字都没有。

也就是说，**这个接口只告诉你「这家店卖这些编码的东西」，而不是「这些东西叫什么、多少钱」。**

这意味着任何「查询菜单 → 展示给用户」的需求，光靠 `query-meals` 是做不到的。你必须再调一次 `calculate-price`：

```json
{
  "storeCode": "1450323",
  "orderType": 1,
  "beType": 1,
  "items": [{"productCode": "9900004064", "quantity": 1}]
}
```

返回：

```json
{
  "success": true,
  "data": {
    "productOriginalPrice": 3450,
    "productPrice": 3450,
    "discount": 0,
    "price": 3450,
    "productList": [{
      "productCode": "9900004064",
      "productName": "精选单人餐三件套",
      "quantity": 1,
      "subtotal": 3450
    }],
    "takeWayList": [
      {"code": "eat-in", "title": "堂食"},
      {"code": "take-in-store", "title": "外带"}
    ]
  }
}
```

`productName` 在这里，`subtotal` 也在这里。

**这个发现顺带给了一条架构原则**：不要在「枚举商品」和「计算价格」之间混用同一份数据。

很多AI 应用的通病是：让模型自己根据商品名字"猜"一个价格，然后展示给用户。这个接口设计上就给了你一个很干净的做法——

> **商品枚举和金额计算严格分离。金额的唯一合法来源是 `calculate-price` 的返回。**

我把这个做成了硬约束：代码里所有价格都从核价响应里取，模型不参与任何价格推算。这样就杜绝了「模型编了一个看起来很合理的价格，用户下单才发现不对」的情况。

---

## 坑三：核价返回「分」，订单接口返回「元」

第三个坑是最经典的，也是最容易翻车的。

看上面那段响应：`"price": 3450`。

如果把它当成元，那这个三件套就是 3450 块——** obviously 不对**。

实际它是**分**，也就是 **34.50 元**。

这个还算好判断。但真正要命的是另一个接口：

```json
{"realTotalAmount": "15.5"}
```

`order-list`（历史订单）返回的 `realTotalAmount` 是一个**字符串的元**——15.5 就是 15.5 元。

**同一个 MCP Server 里，两个接口的金额单位方向相反：**

| 接口 | 字段 | 类型 | 单位 |
|---|---|---|---|
| `calculate-price` | `price` / `discount` / `productPrice` | integer | **分** |
| `order-list` | `realTotalAmount` | string | **元** |

你要是想做一个「算月度支出」的功能，把这两个接口的数值直接加在一起，会得到一个**量级完全错误的数字**——而且很可能不会报错，只是静静地算错。

还有两个相关的细节：

**`order-list` 不接受任何参数。** 我一开始按其他接口的习惯传了参数，反而校验失败。

**历史订单里混着退款单。** `orderStatus` 里会有「整单退款」，如果你不过滤，月度支出会虚高——退掉的那单也算进去了。

---

## 附带的知识点：`list-nutrition-foods` 没有咖啡因

我做的 Skill 是夜班场景，核心功能之一是「根据目标入睡时间倒推咖啡因红线」。

查营养数据时发现，`list-nutrition-foods` 的返回字段是：

> 能量、蛋白质、脂肪、碳水化合物、钠、钙

**没有咖啡因。**

也就是说，任何声称「用麦当劳 MCP 数据帮你控制咖啡因摄入」的功能，咖啡因数据都不可能来自这个接口。唯一的来源是本地基准表。

这不是什么大问题，但它是**一个必须诚实标注的事**：

> 咖啡因数据来自本地公开基准表（mg/中杯），不是 MCP 实时数据。

我把这个声明写进了 README、参赛声明和 Skill 说明里。**在AI 应用里，模糊数据来源比缺功能更危险** —— 用户会默认你给的是实时数据。

---

## 把坑固化成代码，而不是写进文档

发现这些契约之后，我做的第一件事不是写篇博客（虽然这篇就是），而是**把它们变成代码里的断言**。

```python
def nearby_store_params(*, be_type, search_type, city=None, keyword=None):
    if be_type not in BE_TYPE:
        raise ContractError(f"beType非法: {be_type}")
    if search_type not in (1, 2):
        raise ContractError(f"searchType 非法: {search_type}")
    if not city and not keyword:
        # 实测：缺一个分别报 600058 / 600050
        raise ContractError("city 与 keyword 至少提供一个")
    ...
```

好处是：

1. **后来的人不用重踩** —— 传错参数立刻抛异常，而不是等服务端返回你看不懂的错误码
2. **文档失效也不怕** —— 契约固化在测试里，服务端改了测试会红
3. **每个断言都有测试覆盖** —— 现在 24 个本地测试，改一行就验证一遍

对做 MCP 应用的人来说，这三条我觉得都适用。

---

## 项目是什么

**NightFuel · 麦麦深夜补给官**

一个面向夜班/加班人群的麦当劳 Skill。核心洞察是：夜班人打开 App 的真实问题**不是「哪套最便宜」，而是「这一夜怎么过，才不会毁掉明天」**。

它做的事：

- **把夜班拆成四阶段**（入夜 / 续航 / 深夜 / 收尾），各阶段的进食和咖啡因策略不同
- **咖啡因红线倒推**：从目标入睡时间反推「最后一杯咖啡」的时刻（入睡时间 − 半衰期 5 小时），配合 FDA/EFSA 的 400mg 日上限做裁决
- **睡眠负担分**：咖啡因残留 + 高钠（口渴影响睡眠）+ 夜宵热量三维加权，深夜时段主动劝减轻食
- **凑单陷阱检测**：`calculate-price` 双向核价，回答「这张券值不值得为它凑单」——有些券为了用需要多买东西，实付反而涨

技术上零第三方依赖（仅标准库），24 个本地测试，DEMO 模式不需要 MCP Token 就能跑通全链路。

---

## 顺便说

这个项目参加的是**麦当劳程序员创意开发大赛**（1024 专场），排名按 GitHub Star 计。

如果这些坑对你有用，欢迎 Star 支持一下：
👉 **https://github.com/lilyco-42/mcd-nightfuel**

验证脚本在 `tools/verify_mcp.py`，**任何人都可以自己跑一遍验证这些结论**（Token 从环境变量读，仓库里没有凭证）：

```bash
export MCD_MCP_TOKEN="你的Token"
python tools/verify_mcp.py
```

参赛作品（如果规则允许的话，也欢迎去看看其他参赛者的思路）：
👉 https://github.com/M-China/mcd-developer-innovation-challenge/issues/505

---

**最后一句话**：官方文档能让你跑通 demo，但真实业务里出问题的永远是那些文档没写的细节。做 MCP 应用的时候，多花两小时实测每个Tool 的参数契约，比读三遍文档有用。

---

*声明：本文提到的实测数据均来自 2026-10-12 对 `https://mcp.mcd.cn` 的真实调用。项目为个人作品，与麦当劳无隶属关系，商标归其权利人所有。*