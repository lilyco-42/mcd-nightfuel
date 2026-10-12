# 麦麦深夜补给官 · NightFuel

> 一个给夜班人群用的麦当劳 Skill：把「一夜」当成一个完整决策周期，而不是点一餐。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Tests](https://img.shields.io/badge/tests-20%20passed-brightgreen.svg)

## 为什么做这个

夜班/加班的人，打开麦当劳 App 的真实问题从来不是「哪套最便宜」——

凌晨 1 点半，你还要再撑三小时，这时候真正需要回答的是：

- 现在这个点，还有门店在卖吗？
- 我今天已经喝了多少咖啡因，**离能睡着还差几杯**？
- 吃完这顿会不会更睡不着？
- 券要不要为了凑单多买东西？

市面上的麦当劳 Skill 大多在回答「怎么点最省」。**NightFuel 回答的是「这一夜怎么过」。**

## 差异化：三个别人没做的点

1. **夜班是完整周期，不是一餐**
   把夜班拆成 `入夜 → 续航 → 深夜 → 收尾` 四阶段，每阶段的进食与咖啡因策略不同。
   别人问「吃什么」，我们问「这一夜怎么排」。

2. **咖啡因红线倒推**
   从**目标入睡时间反推**「最后一杯咖啡」的时刻（入睡时间 − 半衰期 5h），
   并按 FDA/EFSA 的 400mg 日上限做裁决。
   全场 493 个参赛 issue 中，只有 1 个涉及咖啡因，且没有人把它和夜班场景绑定。

3. **睡眠负担分**
   咖啡因残留 + 高钠（影响口渴睡眠）+ 夜宵热量三个维度打分，
   不让用户「吃完这一顿就更睡不着」。

> 📌 数据来源诚实声明：麦当劳 MCP `list-nutrition-foods` 返回能量、蛋白质、脂肪、碳水化合物、钠、钙，
> **不含咖啡因字段**。因此咖啡因用量取自本地公开基准表（`src/nightfuel/caffeine.py`），
> 我们**不会把估算值说成 MCP 实时数据**。

## 效果

```text
## 今夜补给包 · 01:30 · 深夜
- 阶段策略：轻食优先，少油少钠，把钠和热量压下去
- 咖啡裁决：还剩 110mg 额度，且未过 02:00 —— 最多再来一杯中杯，之后转无咖啡因饮品。
- 建议停止进食：05:00（睡前 2 小时）
- 阶段推荐：麦香鱼、麦茶
- 睡眠负担：钠 1025mg 偏高，口渴影响睡眠，建议配无糖饮品
```

## 安装

### 作为 WorkBuddy Skill

```bash
git clone https://github.com/lilyco-42/mcd-nightfuel.git
cp -r mcd-nightfuel ~/.workbuddy/skills/nightfuel
```

重启 WorkBuddy 后即可用。对话里说「我现在夜班，凌晨一点半，还想再撑三小时」就会触发。

### 配置麦当劳 MCP

复制 `mcp-config.example.json`，把占位符换成你的 Token：

```bash
export MCD_MCP_TOKEN="你的 Token"    # Token 申请：https://open.mcd.cn/mcp
```

Claude Code / Cursor / WorkBuddy 等支持 Streamable HTTP + `Authorization: Bearer` 的客户端均可接入。
详见 [`MCP_INTEGRATION.md`](MCP_INTEGRATION.md)。

## 使用示例

| 你说 | 它做什么 |
|---|---|
| 凌晨一点半还要再撑三小时 | 判阶段→ 查在售 → 算咖啡红线 → 出补给包 |
| 今天喝了两杯美式，两点睡行吗 | 400mg 预算裁决 + 截止时刻倒推 |
| 这张券要我凑单吗 | `calculate-price` 双次核价 + 凑单陷阱检测 |
| 凌晨三点还有麦当劳吗 | 定位门店 → `query-meals` 确认实际在售 |

## 本地运行（无需 Token）

引擎逻辑完全可离线验证，方便二次开发：

```bash
python -m unittest discover -s tests -v                                  # 20 passed
PYTHONPATH=src python -m nightfuel plan --now 01:30 --sleep 07:00 --consumed 290 --demo
PYTHONPATH=src python -m nightfuel trap                                 # 凑单陷阱演示
```

零第三方依赖，仅标准库。

## 项目结构

```
├── SKILL.md# WorkBuddy Skill 主体（也是技术说明）
├── MCP_INTEGRATION.md               # MCP Server / Tool / 调用流程（参赛必交）
├── CONTEST_DECLARATION.md           # 参赛声明（参赛必交）
├── mcp-config.example.json          # 脱敏 MCP 配置示例（参赛必交）
├── workbuddy.md                     # WorkBuddy 上下文（专项奖励必交）
├── src/nightfuel/
│   ├── mcp_adapter.py               # 字段映射 / 单位换算 / 契约校验 / 凑单陷阱检测
│   ├── caffeine.py                  # 咖啡因预算 + 睡眠负担分
│   ├── planner.py                   # 夜班四阶段决策周期引擎
│   ├── demo_data.py                 # DEMO 样本（无真实价格）
│   └── cli.py                       # 命令行入口
└── tests/test_nightfuel.py          # 20 个本地测试
```

## 目标用户

夜班护士 / 值班运维 / 深夜客服 / 便利店与餐饮夜班 / 赶稿的设计与开发 / 考试周备考 / 夜间司机。
次级用户：任何「作息不规律 + 靠麦当劳续命」的人。

## 安全边界

- 所有写操作（`create-order` / `auto-bind-coupons` / `cancel-order`）**默认拦截**，必须二次确认
- Token 仅走环境变量，仓库内不含任何真实凭证
- 任何价格不在 DEMO 模式下被当作实时数据

## 许可证

MIT，见 [LICENSE](LICENSE)。

本项目为个人参赛作品，与麦当劳、腾讯WorkBuddy 无隶属或背书关系。McDonald's、麦当劳及相关标识归其权利人所有。