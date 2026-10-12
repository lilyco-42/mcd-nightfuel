# fixtures —— 录制的真实 MCP 响应

这些文件由 `tools/record_fixtures.py` 从 `https://mcp.mcd.cn` **真实调用录制**，
供 `demo.py` 与测试在无 Token 环境下复现链路。

| 文件 | 来源 Tool |
|---|---|
| `stores.json` | query-nearby-stores（真实返回） |
| `menu.json` | query-meals（真实返回） |
| `prices.json` | calculate-price（真实返回） |
| `nutrition.json` | list-nutrition-foods（真实返回） |
| `coupons.json` | available-coupons（真实返回） |
| `campaign.json` | campaign-calendar（真实返回） |

> 只录制公开数据（门店 / 菜单 / 核价 / 营养 / 可领券 / 活动日历）。
> **不录制账户级数据**（`query-my-account` 积分、`query-my-coupons` 我的券）。
> 录制内容不含 Token、手机号、收货地址等敏感信息。
