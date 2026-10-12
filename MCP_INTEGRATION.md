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

### 2.3 实测发现的调用契约（重要）

以下细节来自对官方 Server 的**实际调用验证**，官方文档未明确说明，但对跑通链路是必需的：

| 发现 | 说明 |
|---|---|
| **门店查询必须带 `beType` + `searchType`** | `query-nearby-stores` 这两个参数为必传，纯经纬度查询会报参数校验失败。到店自提 `beType=1`；`searchType=1` 收藏门店、`2` 按位置 |
| **菜单与券查询必须传三件套** | `query-meals` / `query-store-coupons` 均要求 `storeCode` + `orderType` + `beType` 同时传入；到店自取为 `orderType=1, beType=1` |
| **`calculate-price` 的商品字段是 `items` 而非 `meals`** | 格式为 `items: [{productCode, quantity}]`，用错字段名直接报参数校验失败 |
| **金额单位是「分」** | `calculate-price` 返回的 `price` / `discount` / `productPrice` 均为**整数分**，展示前必须 `/100` |
| **`calculate-price` 会回传门槛差额** | `enjoyable.balance` 表示「距可享受优惠还差多少分」，这是凑单值不值得的**官方数据支撑**，无需自行推算 |
| **`order-list` 的金额单位是「元」，且是字符串** | `realTotalAmount` 形如 `"15.5"`，与 `calculate-price` 的「分」**完全相反** |
| **`order-list` 无需任何参数** | 传参反而校验失败 |
| **历史订单含退款单** | `orderStatus` 有「整单退款」，必须过滤，否则消费画像虚高 |
| **`list-nutrition-foods` 不含咖啡因** | 仅返回能量、蛋白质、脂肪、碳水化合物、钠、钙；咖啡因需另取基准数据 |
| **限流** | 超过 600 次/分钟返回 429 |

> ⚠️ **最容易出错的地方**：`calculate-price` 单位是「分」，`order-list` 是「元」，两者方向相反。

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