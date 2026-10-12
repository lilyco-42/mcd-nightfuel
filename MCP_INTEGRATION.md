# MCP 集成说明

本文档说明 NightFuel 实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

---

## 一、使用的 MCP Server

| 项 | 值 |
|---|---|
| 名称 | 麦当劳中国 MCP Server（`mcd-mcp`） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| 开放平台 | <https://open.mcd.cn/mcp> |
| 官方文档 | <https://github.com/M-China/mcd-mcp-server> |

> 本项目仅通过官方托管 Server 调用，未做任何反向工程或绕过鉴权的访问。
> Token 通过环境变量 `MCD_MCP_TOKEN` 注入，仓库内不包含任何真实凭证。

---

## 二、使用的 Tool 清单

### 2.1 核心链路 Tool（决策主干）

| Tool | 用途 | 在本项目中的角色 |
|---|---|---|
| `now-time-info` | 获取当前时间 | 判定夜班第几小时、归一化咖啡因倒推的起点 |
| `query-nearby-stores` | 查询地址附近可用门店 | 确定「此刻是哪家店」——深夜营业状态的第一前提 |
| `query-meals` | 查询当前门店可售餐品 | 确认**此刻真实在售**，杜绝「推荐一个买不到的」 |
| `list-nutrition-foods` | 餐品营养（能量/蛋白质/脂肪/碳水/钠/钙） | 睡眠负担分的能量与钠维度 |
| `query-store-coupons` | 当前门店可用优惠券 | 提供券约束，驱动凑单陷阱判断 |
| `calculate-price` | 按商品列表（含券）计算金额与优惠 | **唯一计价来源**，所有金额由此得出 |

### 2.2 辅助 Tool（增强体验）

| Tool | 用途 | 在本项目中的角色 |
|---|---|---|
| `available-coupons` | 可领取的麦麦省券 | 提示「先去领券，还能再省多少」 |
| `query-my-coupons` | 账户全部可用券 | 跨门店券面信息补充 |
| `auto-bind-coupons` | 一键领券 | **写操作**，仅在用户确认后调用 |
| `query-order` / `order-list` | 订单详情 / 历史订单 | 还原夜间高频单品与消费习惯 |
| `query-my-account` | 积分账户信息 | 判断积分兑换是否值得 |
| `campaign-calendar` | 当月营销活动 | 判断今夜是否有专属活动 |

### 2.3 实测发现的调用契约（⚠️ 全部经真实调用验证，2026-10-12）

本项目的契约不是抄文档，而是**逐条实测出来的**。官方 README 未写明的部分，
以本节表格为准；每条都在 `src/nightfuel/mcp_adapter.py` 中固化为**运行时断言**，
并在 `tests/test_nightfuel.py` 中有对应回归测试。

| 发现 | 说明 |
|---|---|
| 🔴 **`query-nearby-stores` 的 `city` 与 `keyword` 必须同时提供** | 只给 `city` 或只给 `keyword` 都会失败：`keyword` 缺失报 `600058 城市名或者关键词不能为空`；`city` 缺失报 `600050 收藏餐厅列表为空，请您提供城市+关键词进行搜索`。实测 `{"city":"上海","keyword":"徐家汇","searchType":2,"beType":1}` 返回成功（门店 `1450323` 上海徐汇漕溪北路百脑汇餐厅） |
| 🔴 **schema 不暴露 latitude/longitude** | 官方 inputSchema 的 properties 只有 `beType` / `city` / `keyword` / `searchType`，**没有经纬度入参**。定位由服务端按 city+keyword 处理，别自造经纬度字段 |
| **必传字段以 inputSchema.required 为准** | `query-nearby-stores` → `["beType","searchType"]`；`query-meals` 与 `calculate-price` → `["storeCode","orderType","beType"]` |
| **`beType` 有 4 个合法值** | `1` 到店自提 / `2` 麦乐送到家 / `5` 得来速车道取餐(Drive Through) / `6` 企业团餐。**只有 1、2 是文档常提的，5 和 6 同样合法** |
| **`beCode` 与 `storeCode` 配对使用** | 从 `query-nearby-stores` 返回结果中一并取回，得来速等场景必填 |
| 🔴 **`query-meals` 只返回 `code` 和 `tags`，没有名称也没有价格** | 实测返回形如 `{"code":"9900004064","tags":["爆款"]}`。**品名与单价必须从 `calculate-price` 的 `productList[].productName` / `subtotal` 反查** —— 这是本项目「枚举与计价分离」的物理依据 |
| 🔴 **`calculate-price` 的金额单位是「分」（已实证）** | 真实返回 `{"price":3450,...,"productName":"精选单人餐三件套"}` → **34.50 元**。同响应含 `productOriginalPrice` / `productPrice` / `originalPrice` / `discount`，均为分 |
| **`calculate-price` 会回传取餐方式** | `takeWayList` 含 `eat-in`（堂食）/ `take-in-store`（外带），可在结果中一并展示 |
| **`calculate-price` 会回传门槛差额** | `enjoyable.balance` 表示「距可享受优惠还差多少分」，是凑单判断的官方依据，无需自行推算 |
| **菜单/券查询必须传三件套** | `query-meals` / `query-store-coupons` 均要求 `storeCode` + `orderType` + `beType`；到店自取为 `orderType=1, beType=1` |
| **`calculate-price` 的商品字段是 `items` 而非 `meals`** | 格式为 `items: [{productCode, quantity}]`，用错字段名直接报参数校验失败 |
| **`order-list` 的金额单位是「元」，且是字符串** | `realTotalAmount` 形如 `"15.5"`，与 `calculate-price` 的「分」**完全相反** |
| **`order-list` 无需任何参数** | 传参反而校验失败 |
| **历史订单含退款单** | `orderStatus` 有「整单退款」，必须过滤，否则消费画像虚高 |
| **`list-nutrition-foods` 不含咖啡因** | `required: []`，返回能量、蛋白质、脂肪、碳水化合物、钠、钙；**无咖啡因字段** |
| **工具总数 35 个** | 以 `tools/list` 实测为准（README 文本中夹有客户端名，勿据此计数） |
| **限流** | 超过 600 次/分钟返回 429 |

> ⚠️ **最容易出错的地方**：`calculate-price` 单位是「分」，`order-list` 是「元」，两者方向相反。
> ⚠️ **最容易漏掉的坑**：`query-meals` 不给品名和价格。不查 `calculate-price` 就无法告诉用户「这个多少钱」。

### 2.4 真实调用验证记录（可复现）

```text
$ python tools/verify_mcp.py        # Token 仅从环境变量读取

0. initialize      → mcd-mcp v1.0.0, protocolVersion 2024-11-05
1. now-time-info   → OK
2. list-nutrition-foods → OK（确认无 caffeine 字段）
3. query-nearby-stores  → city+keyword 必填（600058 / 600050 已复现）
4. query-meals     → OK（仅 code/tags）
5. calculate-price → price=3450（分）= 34.50 元 精选单人餐三件套
6. query-my-coupons / available-coupons / query-my-account → OK
```

验证脚本 `tools/verify_mcp.py` 不含任何 Token，仅从环境变量 `MCD_MCP_TOKEN` 读取。
验证过程**未调用任何写操作**（未下单、未领券、未取消订单）。

上述契约已在 `src/nightfuel/mcp_adapter.py` 中以**运行时断言**固化（`ContractError`），
并在 `tests/test_nightfuel.py` 中有对应测试，不会因文档缺失而靠猜。

---

## 三、调用流程

### 链路 A：今夜补给包（主链路）

```text
用户：现在凌晨一点半，还要再撑三小时
  │
  ├─ 1. now-time-info                      → 01:30
  ├─ 2. caffeine_budget(sleep=07:00)        → 截止 02:00 → one_more（还剩110mg）
  │    ※ 跨零点归一：07:00 > 01:30，同轴比较
  ├─ 3. query-nearby-stores                → 定位门店（beType+searchType 必传）
  ├─ 4. query-meals                        → 该门店此刻真实在售
  ├─ 5. list-nutrition-foods               → 能量/钠 → 睡眠负担分
  ├─ 6. query-store-coupons                → 券约束
  ├─ 7. calculate-price                    → 唯一计价来源（分）
  └─ 8. 输出「今夜补给包」                  → 阶段/咖啡裁决/停止进食时间/推荐/负担
```

### 链路 B：券是否值得凑单（回答多数工具不答的问题）

```text
用户：这单用券要我凑单吗
  │
  ├─ query-store-coupons    → 取券门槛
  ├─ calculate-price（基线）→ price / enjoyable.balance
  ├─ calculate-price（+凑单商品）→ price
  └─ detect_coupon_trap()   → 实付不降反升 → 明确「不凑单」+ 给对照方案
```

多数工具只回答「怎么用券最省」，本项目额外回答「**这张券值不值得为它凑单**」。

### 链路 C：写操作（严格拦截）

```text
用户：那就下单吧
  │
  ├─ create-order / auto-bind-coupons / cancel-order
  └─ ⚠️ 硬拦截：必须先展示完整方案 + 用户明确确认，禁止自动连问、禁止静默下单
```

---

## 四、业务价值

| 场景 | 现有工具的缺口 | NightFuel 的回答 |
|---|---|---|
| 凌晨 1 点半 | 通用点餐工具给「最省的套餐」，不问你还要撑多久 | 四阶段策略 + 按入睡时间倒推的咖啡因红线 |
| 睡不着 | 只报咖啡因总量，不管你几点睡 | 截止时刻倒推 + 睡前 2h 停止进食 |
| 券要不要凑 | 只答「怎么最省」 | 双次核价 + 凑单陷阱检测，明确劝阻 |
| 深夜想吃 | 不保证门店此刻在售 | `query-meals` 实时确认在售 |

---

## 五、隐私与安全

- Token 仅从环境变量 `MCD_MCP_TOKEN` 读取，仓库内无真实凭证，配置示例仅含占位符
- 写操作硬拦截 + 二次确认，不自动连问、不静默下单
- 未做反向工程，仅使用官方文档公开的 Tool