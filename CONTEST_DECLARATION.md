# 参赛声明

## 原创性声明

本项目 **麦麦深夜补给官（NightFuel）** 为参赛者独立开发的原创作品。

- 项目创建于 2026 年，符合活动要求的「2025-12-25 至 2026-10-25」时间窗口
- 全部源代码（`src/nightfuel/`、`tests/`）、文档与配置文件均由参赛者本人撰写
- 未复制、抄袭或改编任何其他参赛者的项目
- 未使用任何来源不明的代码片段

## 真实使用麦当劳 MCP 声明

本项目真实调用麦当劳官方 MCP Server（`https://mcp.mcd.cn`）：

- 使用其官方文档公开的 Tool：`now-time-info`、`query-nearby-stores`、`query-meals`、
  `list-nutrition-foods`、`query-store-coupons`、`calculate-price`、
  `available-coupons`、`query-my-coupons`、`query-my-account`、`campaign-calendar`、
  `order-list` / `query-order`，以及写操作 `create-order`、`auto-bind-coupons`、`cancel-order`
- **未做任何反向工程、协议破解或绕过鉴权的访问**
- 未硬编码任何真实 Token，凭证仅从环境变量 `MCD_MCP_TOKEN` 注入

详细 Tool 清单、调用流程与实测调用契约见 [`MCP_INTEGRATION.md`](MCP_INTEGRATION.md)。

## 数据来源声明

为避免误导，本项目对两类数据做了严格区分：

1. **MCP 实时数据**：门店、真实在售餐品、优惠券、营养（能量/蛋白质/脂肪/碳水化合物/钠/钙）、
   计价金额 —— 全部来自麦当劳 MCP
2. **本地基准数据**：**咖啡因含量**。
   麦当劳 MCP `list-nutrition-foods` **不返回咖啡因字段**，
   因此本项目的咖啡因数值取自 `src/nightfuel/caffeine.py` 中的 `CAFFEINE_MG` 本地基准表
   （公开资料整理，单位 mg/中杯），并在 `SKILL.md` 中明确标注为估算基准，
   **绝不冒充 MCP 实时数据**。

公开健康标准引用说明：成人每日咖啡因上限 400mg、咖啡因半衰期约 5 小时，
来自 FDA / EFSA 公开健康建议，非商业用途。

## 敏感信息与凭证声明

- 仓库内**不包含**任何真实 MCP Token、账号、手机号、地址等敏感信息
- `mcp-config.example.json` 仅含环境变量占位符 `${MCD_MCP_TOKEN}`
- 代码中不写入、不打印、不传输任何凭证
- 位置信息（经纬度）仅在运行时由用户主动提供并用于单次门店查询

## 合规声明

- 本项目内容符合中华人民共和国相关法律法规及 GitHub 平台规则
- 不含政治敏感内容，不含违反社会主义核心价值观的内容
- **不贬低、不讽刺、不诋毁麦当劳品牌、产品或形象**，不对麦当劳与其他品牌作贬损性对比
- 不宣扬不健康饮食方式、奢靡浪费、拜金主义等观念：
  本项目主张在作息不规律的时段**更合理地安排饮食节奏与咖啡因摄入**，而非鼓励无节制消费
- 不含赌博、迷信、色情、暴力、侵权内容
- 不植入恶意脚本、钓鱼链接，不指向违规站点
- 不收集、不上传用户个人信息

## 关联关系声明

本项目为个人参赛作品，**与麦当劳、腾讯 WorkBuddy 无隶属或背书关系**。
「麦当劳」「McDonald's」「巨无霸」等商标归其权利人所有。
本项目使用的均为官方公开文档中的 MCP 能力，未使用任何未公开接口。

## 原创数据声明

`src/nightfuel/demo_data.py` 中的 DEMO 餐品名称与营养数值为公开常识整理，
**不含真实门店价格**；所有金额在真实运行时均以 MCP `calculate-price` 返回为准。