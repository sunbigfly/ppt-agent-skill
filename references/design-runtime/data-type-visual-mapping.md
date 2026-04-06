# 数据类型 -> 视觉呈现参考索引

> 本表将 brief 中的核心数据类型（metrics、timelines、before_after 等 40+ 种）严格映射到工程上的 `card_type`、`layout_hint` 和最佳 CSS 实现参考。
> **铁血纪律**：本表是架构引擎的刚性映射组件库，绝非供人随意弃用的“灵感”。Planning sub-agent 在设定好“视觉焦点与动线”后，遇到特定的数据类型，**必须首选在此表内选取最优解去承接**。自由的代价就是质量崩塌与结构散乱，请严格向最佳实践收敛。
> 覆盖 8 大类：数据展示、商业分析、对比论证、流程结构、叙事内容、技术学术、进度状态、团队与地理。

本表是 **上游资料整理 / brief 结构化 -> Step 4（Planning）-> Step 4（HTML）** 的桥梁。

- 上游资料整理阶段参考"数据类型"列，识别并格式化原始资料
- Step 4 的 Planning sub-agent **按需查阅**"推荐 card_type"和"推荐布局"列获取灵感，但最终选择由设计意图驱动
- Step 4 的 HTML sub-agent 参考"CSS 实现参考"列，选择渲染技法

## 数据展示类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `data_tables` | `data` / `comparison` | symmetric / three-column | 标准 `<table>` + 斑马纹 + 高亮行 | evidence / comparison |
| `metrics` | `data_highlight` | hero-top / primary-secondary | `charts/kpi.md` `charts/metric-row.md` | cover / evidence / close |
| `kv_pairs` | `data` / `list` | symmetric / primary-secondary | 标签+值两列布局，标签半透明 | setup / evidence |
| `matrix_data` | `matrix_chart` | single-focus / primary-secondary | `blocks/matrix-chart.md` 2x2 grid | comparison / framework |
| `funnel_data` | `data` | single-focus / primary-secondary | `charts/funnel.md` 梯形递减 | process / evidence |
| `pie_data` | `data` | primary-secondary | `charts/ring.md` 环形图 + 图例 | evidence / comparison |
| `trend_series` | `data` | primary-secondary / hero-top | `charts/sparkline.md` 折线 + 标注 | evidence / close |
| `ranked_list` | `list` / `data_highlight` | l-shape / asymmetric | 排名编号 + 渐变条 + 数值 | evidence / comparison |
| `score_card` | `data` | single-focus | `charts/radar.md` 雷达图 | evidence / comparison |
| `distribution_data` | `data` | primary-secondary | `charts/stacked-bar.md` 堆叠柱状 | evidence |

## 商业分析类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `swot` | `matrix_chart` | single-focus | 2x2 彩色网格，每象限独立色 | framework / comparison |
| `pricing_plans` | `comparison` | symmetric / three-column | 卡片并列 + 推荐高亮 + 勾选列表 | comparison / close |
| `cost_breakdown` | `data` | primary-secondary | `charts/stacked-bar.md` + `charts/ring.md` 占比 | evidence / process |
| `competitive_matrix` | `comparison` / `matrix_chart` | single-focus / symmetric | 多列对比表 + 评分色块 | comparison |
| `value_chain` | `process` | l-shape / waterfall | 箭头链 + 每段 value_add 标注 | framework / process |

## 对比论证类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `before_after` | `comparison` | symmetric | 左右分栏 + 对比色 + 箭头 | evidence / comparison |
| `pros_cons` | `comparison` | symmetric | 双列 + 绿勾/红叉图标 | comparison / framework |
| `scenario_comparison` | `comparison` | symmetric / three-column | 场景卡片 + 结果高亮 | comparison / close |

## 流程结构类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `timelines` | `timeline` | l-shape / waterfall | `blocks/timeline.md` `charts/timeline.md` | process / evidence |
| `process_flows` | `process` | l-shape / waterfall | 步骤编号 + 连接线 + warning 高亮 | process / framework |
| `parallel_items` | `list` / `data` | symmetric / three-column | 并列卡片 + icon + 统一字号 | evidence / setup |
| `hierarchies` | `diagram` | single-focus / t-shape | `blocks/diagram.md` 嵌套缩进 / 树形 | framework |
| `cycle_flow` | `process` / `diagram` | single-focus | 环形箭头布局 + 中心标题 | framework / process |
| `decision_tree` | `diagram` | single-focus / l-shape | 分支线 + 条件标签 + 结果节点 | framework / process |
| `pyramid_layers` | `diagram` | single-focus | 多层梯形/三角 + 从上到下递进 | framework |
| `stakeholder_map` | `diagram` | single-focus | 同心圆 + 实体标签 | framework / setup |
| `journey_map` | `process` / `timeline` | waterfall / l-shape | 多泳道横向流程 + 情绪曲线 | framework / process |

## 叙事内容类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `definitions` | `text` | primary-secondary | 术语加粗 + 解释正文 + 分割线 | setup / evidence |
| `milestone_results` | `data_highlight` | hero-top / symmetric | `charts/kpi.md` 大数字 + 成就描述 | close / cta |
| `user_testimonials` | `quote` / `people` | asymmetric / primary-secondary | `blocks/quote.md` `blocks/people.md` | evidence / close |
| `faq_pairs` | `list` / `text` | l-shape / symmetric | Q 加粗 + A 缩进 + 折叠展开 | setup / evidence |
| `number_highlights` | `data_highlight` | hero-top / single-focus | `charts/kpi.md` 超大字号 + 单位 + 上下文 | cover / close / evidence |
| `story_arc` | `timeline` / `text` | waterfall / l-shape | 三幕式横向流 + 情绪标注 | setup / evidence |
| `expert_quotes` | `quote` | primary-secondary / asymmetric | `blocks/quote.md` + 头像 + 机构 | evidence / setup |
| `checklist` | `list` | l-shape / symmetric | 勾选框 + 完成状态色 | process / close |
| `analogy_pairs` | `text` / `comparison` | symmetric | 左列"已知" + 右列"目标" + 映射箭头 | setup / framework |

## 技术学术类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `code_snippets` | `text` | primary-secondary / single-focus | `<pre><code>` + 语法高亮 + 行号 | evidence / framework |
| `experiment_results` | `data` / `comparison` | primary-secondary | 假设-方法-结果三段 + 数据表 | evidence |
| `architecture_diagram` | `diagram` | single-focus / t-shape | `blocks/diagram.md` 分层盒子 + 连接线 | framework |
| `formula_data` | `text` | primary-secondary | 公式居中大字 + 变量说明列表 | evidence / framework |

## 进度状态类

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `progress_tracker` | `data` / `list` | l-shape / symmetric | `charts/progress-bar.md` 进度条 + 状态色 | process / close |
| `gantt_data` | `timeline` | waterfall / single-focus | 横向条状 + 时间刻度 + 依赖线 | process / framework |
| `status_dashboard` | `data` / `list` | mixed-grid | 分类标签 + 状态色块(绿/黄/红) | process / close |
| `action_items` | `list` | l-shape / symmetric | 任务 + 负责人标签 + 截止日 | close / cta |
| `risk_items` | `data` / `list` | l-shape / symmetric | 风险色块(红/黄/绿) + 缓解措施 | process / close |

## 团队与地理

| 数据类型 | 推荐 card_type | 推荐布局 | CSS 实现参考 | 适用页面类型 |
|---------|---------------|---------|-------------|------------|
| `team_profiles` | `people` | symmetric / three-column | `blocks/people.md` 头像 + 姓名 + 职位 | setup / close |
| `geographic_data` | `data` | single-focus / primary-secondary | 区域列表 + 高亮标记 + 数值色阶 | evidence |
| `image_candidates` | `image_hero` | hero-top / l-shape | `blocks/image-hero.md` | cover / section |

---

## card_type 扩展建议

当前 card_type 枚举（13 种）：

```
text | data | list | process | tag_cloud | data_highlight | timeline | diagram | quote | comparison | people | image_hero | matrix_chart
```

说明：`process` 是 validator 合法的原生 `card_type`，但当前没有独立的 `blocks/process.md`。使用它时，不要期待 `resource_loader resolve` 自动拿到专属 block 正文；应结合 `layout_refs`、`principle_refs`、`director_command` 和必要的 chart 资源共同落地。

建议扩展（+9 种）：

```
+funnel        → 漏斗可视化
+pie_ring      → 饼图/环形图
+trend_chart   → 趋势折线图
+ranked        → 排行榜
+score_radar   → 评分雷达图
+cycle         → 循环流程图
+pyramid       → 金字塔/分层图
+journey       → 用户旅程图
+code_block    → 代码片段
```

扩展后共 22 种 card_type，每种都有对应的 CSS 实现参考和区块文档。

---

## 高级架构师的组合逻辑（如何消费本表）

这个表格提供了极其明确的数据到视觉的物理通道映射。

1. **降维重组**：如果你认为能够更完美地传达意图，你完全可以将 `metrics` 使用 `asymmetric`（不对称）或者甚至是 `waterfall` 布局。
2. **跨界调用**：你可以把枯草的数据表格 `data_tables` 投放到为 `competitive_matrix` 设计的体系中运转。
3. **重型声明**：在策划稿中，当你的布局组合越级跨用了这套标准，就越要在 `resource_rationale` 和 `prose` 中把你的空间物理依据逻辑写清，确保你的选配不是随意拍脑门而是具备严谨的容器自洽性，HTML 层才能安全渲染！。
