# 采访问卷共享核心

> 本文件是 Step 0 的共享采访内容合同，不直接作为运行时 prompt 发给主 agent。
> 运行时应按能力选择 `tpl-interview-structured-ui.md` 或 `tpl-interview-text-fallback.md`。

## 核心采访目标（执行指南）

作为系统首个守门节点，必须以最高效的轮次获取极高信噪比的输入。核心目标：不与用户寒暄，直接锁定能左右大纲结构、视觉风格和管线分支的关键维度参数。

## 必须覆盖的 4 组维度（另加 1 组人工审计扩展）

你向用户抛出的选项，必须精准涵盖基础 4 组维度域，并额外补上 1 组人工审计扩展维度。

### A. 业务场景与传达目标

左右内容深度与叙事基调。

- `presentation_scenario`（落盘归一化到 `scenario`）: 新人介绍 / 内部汇报 / 社区宣讲 / 招商合作 / 融资路演 / 大众科普等
- `core_audience`（落盘归一化到 `audience`）: “你是谁，要在台上向谁讲？” 如一线操盘手向高层要资源 / 业务一号位向客户布道 / 讲师向小白泛大众科普
- `target_action`: 建立认知 / 促成意向 / 愿意加入 / 纯信息同步

### B. 结构密度与生产管线

左右大纲页数、图文排布与数据源获取。

- `expected_pages`: 5-10 页 / 10-20 页 / 20-30 页宽幅 / 自由发挥
- `page_density`: 少而精 / 适中 / 容量极大（注意：这是整套 deck 的整体倾向，不是要求每一页完全同密）
- `material_strategy`: `research`（全网扩写）或 `local_only`（仅限当前提供资料）
- `must_include` / `must_avoid`: 可要求用户补充唯一核心主张与绝对禁区

### C. 视觉审美与资产策略

左右后续 Style / HTML 生成器的美学锁。

- `visual_style`（落盘归一化到 `style`）: 极简商务 / 科技极客 / 轻量活泼 / 自动匹配
- `language_mode`（落盘归一化到 `language`）: 中文 / 英文 / 中英混排
- `imagery_strategy`（落盘归一化到 `imagery`）: decorate / generate / provided / manual_slot
- `brand_constraints`（落盘归一化到 `brand`）: 品牌视觉禁忌、主色、字体偏好、Logo 使用边界

### D. 构建环境与工程卡口

- `success_criteria`: 用户评价标准
- `subagent_model_strategy`: 继承主代理 / 指定更强模型 / 指定更快模型
- `subagent_thinking_effort`: 低 / 中 / 高

### E. 人工审计与断点控制

- `manual_audit_mode`: `off`（不参与） / `milestone_only`（只看关键节点） / `fine_grained`（细颗粒度断点）
- `manual_audit_scope`: 想介入哪些节点，如 `outline` / `style` / `page_planning` / `page_html` / `page_review`
- `manual_audit_assets`: `summary_only`（只看主 agent 摘要） / `png_only`（看图） / `runtime_and_selected_assets`（允许直接点 runtime / html / 指定审查图）

## 字段归一化映射

采访阶段优先使用上面的 canonical 采集名；写盘时统一归一化到 validator 与下游 playbook 现在消费的锚点名。

| 采集字段 | 写入 `interview-qa.txt` / `requirements-interview.txt` 的锚点 |
|---|---|
| `presentation_scenario` | `scenario` |
| `core_audience` | `audience` |
| `target_action` | `target_action` |
| `expected_pages` | `expected_pages` |
| `page_density` | `page_density` |
| `visual_style` | `style` |
| `brand_constraints` | `brand` |
| `must_include` | `must_include` |
| `must_avoid` | `must_avoid` |
| `language_mode` | `language` |
| `imagery_strategy` | `imagery` |
| `material_strategy` | `material_strategy` |
| `subagent_model_strategy` | `subagent_model_strategy` |
| `subagent_thinking_effort` | `subagent_thinking_effort` |
| `manual_audit_mode` | `manual_audit_mode` |
| `manual_audit_scope` | `manual_audit_scope` |
| `manual_audit_assets` | `manual_audit_assets` |

## `interview-qa.txt` 写盘锚点（强制）

所有问卷结果必须映射到以下两份产物，作为后续子代理的真源输入。

1. `interview-qa.txt`
   保留用户原意。为通过 `contract_validator.py` 强校验，结尾必须附加 canonical 锚点段。基础 12 个锚点缺一不可，同时默认追加模型与人工审计锚点：
   `scenario`, `audience`, `target_action`, `expected_pages`, `page_density`, `style`, `brand`, `must_include`, `must_avoid`, `language`, `imagery`, `material_strategy`, `subagent_model_strategy`, `subagent_thinking_effort`, `manual_audit_mode`, `manual_audit_scope`, `manual_audit_assets`

2. `requirements-interview.txt`
   脱水的纯净参数组，同样必须包含上方基础 12 个锚点，以及模型 / 人工审计锚点，并带上丰富化后的明确取值，供 validator、Style、Outline、PageAgent 与后续人工返工节点直接消费。
   若主 agent 已完成归一化，可额外补充 `density_bias: relaxed/balanced/ultra_dense` 作为内部派生字段；未补充时，下游必须根据 `page_density` 自行推导，不得报错。
