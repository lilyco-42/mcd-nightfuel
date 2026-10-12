---
name: nightfuel
description: >
  麦麦深夜补给官：面向夜班/加班/夜间值守人群的麦当劳 MCP 全链路 Skill。
  把「一夜」当成一个完整决策周期——按入夜/续航/深夜/收尾四阶段给出今夜补给包：
  现在该吃什么、咖啡因还能不能喝（按目标入睡时间倒推红线）、几点前停止进食，
  所有价格与在售状态均来自麦当劳 MCP 实时核价。Use when 用户提到夜班、熬夜、加班、
  深夜还没睡、值班、凌晨想吃麦当劳、今天喝了多少咖啡、睡不着、咖啡因、熬夜吃什么、
  night shift, late night, overtime, caffeine, sleep。Also use for 麦当劳点餐决策、
  券是否值得凑单、深夜门店是否还营业等场景。
agent_created: true
---

# 麦麦深夜补给官 NightFuel

夜班/加班人群的真实痛点不是「怎么点最省」，而是**「这个点、这个状态、这一夜该怎么吃，才不会毁掉明天」**。

本Skill 不做「一餐推荐」，做**一夜的补给决策**：把夜班拆成四个阶段，每阶段的进食策略、
咖啡因配额、睡眠负担都不同，最后收敛成一份「今夜补给包」。

## 何时使用

- 用户提到夜班 / 熬夜 / 加班 / 值班 / 凌晨 / 深夜 / 还没睡
- 用户问「今天喝多少咖啡」「睡不着」「咖啡因」「熬夜吃什么」
- 用户问深夜还能不能点到、某家店这个点有没有在售

## 核心约束（违反即出错）

1. **禁止编造价格**：所有金额必须来自 MCP `calculate-price`。没有实时数据就明确说「需实时核价」。
2. **禁止编造在售状态与品名**：必须先 `query-meals` 确认门店当前在售；
   ⚠️ `query-meals` 只返回 `code` 和 `tags`，**没有名称也没有价格**，
   品名与单价必须从 `calculate-price` 的 `productList[].productName` / `subtotal` 反查。
3. **咖啡因数据不是 MCP 的**：`list-nutrition-foods` 只有能量/蛋白质/脂肪/碳水/钠/钙，**不含咖啡因**。
   咖啡因用本地基准表（见 `src/nightfuel/caffeine.py` 的 `CAFFEINE_MG`），回答时要说明这是估算基准而非 MCP 实时值。
   半衰期 5h 与 400mg 上限的公开依据见 [`references/night-shift-physiology.md`](references/night-shift-physiology.md)。
4. **写操作默认拦截**：`create-order` / `auto-bind-coupons` / `cancel-order` 一律先展示方案 + 二次确认，
   用户明确同意后才调用。不得在一次对话里自动连问。
5. **单位陷阱**：`calculate-price` 返回**分**（实测 `price=3450` → 34.50 元），`order-list` 返回**元的字符串**，两者相反，混用=数量级错误。
6. **门店查询必须同时给 city 和 keyword**：只给其一分别报 `600058`（缺 keyword）/ `600050`（缺 city）。
   schema 也**没有经纬度入参**，别自造字段。
7. **查菜单前先查营业状态**：`query-nearby-stores` 返回 `businessStatus`（布尔）与
   `businessStartTime` / `businessEndTime`。**深夜场景必须先看这个字段**——非 24h 门店在非营业时段
   查菜单会报 `600057 门店可能已关闭或不在营业时间`。凌晨 1 点用户问「还有麦当劳吗」，
   正确答案就是这个字段，不是一句错误码。24h 门店表现为 `00:00` - `23:59`。
8. **商品售罄会单独报错**：`60006 商品已售罄或不可售`。写商品编码时不要假设长期在售，
   报错时换同品类商品（实测：蓝莓派 521950 已下架，麦香鱼 9900015856 正常在售）。

## 执行链路（按顺序）

```
1. now-time-info                 → 当前时间，判定夜班第几小时
2. caffeine_budget()             → 按目标入睡时间倒推咖啡因红线，裁决 stop/one_more/ok
3. query-nearby-stores           → city + keyword + beType + searchType（四项缺一不可）
   └─ 先看返回的 businessStatus → false 就直接告诉用户「这家店现在打烊」+ 给营业时间，
      不要继续查菜单（否则 600057）
4. query-meals                   → 确认该门店此刻真实在售（storeCode+orderType+beType）
   ⚠️ 只返回 code/tags，品名与价格要靠下一步反查；遇 60006 换同品类在售商品
5. calculate-price               → 唯一计价来源；品名/单价也从这里取（单位：分）
6. list-nutrition-foods          → 能量/钠，叠加咖啡因基准表 → 睡眠负担分
7. query-store-coupons           → 该门店可用券
8. detect_coupon_trap()          → 双次核价，回答「这张券值不值得为它凑单」
9. 输出「今夜补给包」             → 阶段 / 咖啡裁决 / 停止进食时间 / 阶段推荐 / 睡眠负担
```

## 咖啡因红线算法

```
截止时刻 = 目标入睡时间 − 半衰期(5h)
每日上限 = 400mg（FDA / EFSA 公开标准）
裁决     = consumed ≥ 400 → stop
           now ≥ 截止时刻  → stop
           距截止 < 1h    → one_more（最后一杯）
           否则            → ok
```

⚠️ **跨零点必须归一到同一时间轴**：入睡时间不晚于当前时间 → 视为次日。
否则「21:00 睡到次日 07:00」会被误判成已过 02:00 截止线（本地测试 `test_midnight_wrap_not_a_day_early` 锁死此场景）。

## 四阶段策略

| 阶段 | 时间 | 策略 |
|---|---|---|
| 入夜 | 18:00–21:00 | 主食打底 + 第一杯咖啡 |
| 续航 | 21:00–01:00 | 顶饱低渣，咖啡配额在这里用掉 |
| 深夜 | 01:00–04:00 | 轻食优先，少油少钠 |
| 收尾 | 04:00–06:00 | 低咖啡因，睡前 2h 停止进食 |

## 睡眠负担分

三个维度加权，满分100：`咖啡因残留 + 高钠(>800mg) + 夜宵热量(>700kcal)`。
≥45 分则建议换轻食或减半。

## 本地验证（无需 MCP Token）

```bash
python -m unittest discover -s tests -v        # 28 个本地测试（含 JS/Python 算法一致性 18 例）
python demo.py                                # 零配置演示：读 fixtures/ 里录制的真实 MCP 响应
PYTHONPATH=src python -m nightfuel plan --now 01:30 --sleep 07:00 --consumed 290 --demo
PYTHONPATH=src python -m nightfuel trap        # 凑单陷阱检测演示
```

DEMO 模式的数字是样本数据，**回答用户时必须标注 DEMO**，不能当成实时价格。

## 追问要点

用户没说清就问，但只问这三条里缺的那条：
1. 目标入睡时间（咖啡因红线必需）
2. 今日已摄入咖啡因（不知道就按0 算，并说明是估算）
3. 位置（定位门店）

不要一次问三个。优先问睡眠时间，其余可默认值推进。