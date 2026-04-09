# Page Planning Playbook -- 单页策划稿

## 目标

制定一张从布局、字体、配图策略到卡片组织的 1280x720 物理画幅精细蓝图。**本阶段只写 JSON，不写 HTML。**

---

## Phase 1：理解当前页定位

从 `outline.txt` 中找到第 N 页的定义，明确：
- `page_goal`：这一页的核心论点（一句话，不含"和"字）
- `narrative_role`：叙事角色（cover/toc/section/evidence/comparison/process/close/cta）
- `proof_type`：论证方式（数据驱动/案例/对比/框架/步骤）
- `密度下限 / 密度目标 / 密度上限`
- `节奏动作 / 信息姿态 / 锚点类型`
- deck 级 `密度倾向` 与整套 `密度曲线`

> **硬边界**：本阶段不是重新发明这一页的密度，而是把 outline 定下的窗口冻结成单页可执行的 `density_contract`。

---

## Phase 2：资源发现与设计决策

运行 `resource_loader.py menu` 获取可用组件菜单后，**你是严密的架构师，不是随性的画家**。必须深刻理解物理数据类型并严丝合缝地对接组件栈：

1. **观众在这一页应该先看到什么？** → 决定你的视觉锚点和主次关系
2. **这一页的信息是怎么“流动”的？** → 决定空间布局和视觉动线
3. **这一页和上一页的视觉感受应该有什么不同？** → 决定节奏变化
4. **在菜单中的工具里，哪些能最好地服务上面 3 个答案？** → 决定 layout_hint、card_type、chart、resource_ref

> **重要**：菜单里的工具是你的工业模具库，不是随手涂鸦的画笔。对于不同的数据虽然可以跨界利用高阶模具，但必须确保逻辑自洽、严防骨架崩塌。

**填写 `resources` 字段时必须说明为什么选择该组件**（`resource_rationale` 字段）。

### 命名合同（必须区分 schema 枚举 与 资源文件 stem）

- `layout_hint` / `page_type`：写 validator 认可的值。`layout_hint` 推荐使用真实文件 stem，如 `hero-top`、`mixed-grid`、`l-shape`。
- 非 `content` 页优先通过 `page_type` 消费 `page-templates/`（如 `cover` / `toc` / `section` / `end`）。通常不需要再写 `layout_hint`；只有在要显式钉住模板正文时，才额外填写 `resources.page_template`。
- `card_type`：写 validator 认可的枚举，如 `data_highlight`、`image_hero`、`matrix_chart`。
- `chart.chart_type`：写 validator 认可的枚举，**使用下划线命名**，如 `metric_row`、`comparison_bar`、`stacked_bar`、`progress_bar`。
- `resources.*_refs` 与 `card.resource_ref.*`：推荐写 `references/` 中的真实文件 stem，如 `metric-row`、`comparison-bar`、`visual-hierarchy`；`resource_loader.py` 会自动做下划线/连字符归一化。
- `process` 是 schema 原生 `card_type`，但当前没有 `blocks/process.md`。若使用它，必须同时给出更强的 `layout_refs`、`principle_refs`、`director_command` 和必要的 `chart_refs` / `resource_ref`，不要假设会有专属 block 正文可加载。

### principle_refs 指导（重要：设计原则文件按场景选用）

`resources.principle_refs[]` 字段决定 HTML 阶段能否收到设计原则正文。按以下规则填写：

| 本页特征 | 应引用 |
|---------|--------|
| 数据图表主导页 | `data-visualization` |
| 多卡片排版，需要层次感 | `visual-hierarchy` |
| 封面/章节页，需要情绪校准 | `color-psychology` |
| 信息超密、担心认知负担 | `cognitive-load` |
| 叙事转折页（从问题到方案）| `narrative-arc` |
| 任何页面的排版构图优化 | `composition` |
| 不确定选哪个 | `design-principles-cheatsheet`（综合速查）|

在 planning JSON 中写法示例：
```json
"resources": {
  "principle_refs": ["visual-hierarchy", "composition"],
  "layout_refs": ["hero-top"],
  "block_refs": [],
  "chart_refs": ["kpi"]
}
```

填写后，`resource_loader.py resolve` 会自动把对应原则文件的完整正文注入 HTML 阶段的上下文。

---

## Phase 3：密度合同冻结（强制）

### 五档基础预算

| `density_label` | `max_cards` | `max_charts` | `min_body_font_px` | `max_lines_per_card` | `image_policy` | `decoration_budget` | `overflow_strategy` |
|---|---:|---:|---:|---:|---|---|---|
| `low` | 2 | 1 | 24 | 3 | `flexible` | `generous` | `rebalance_layout` |
| `mid_low` | 3 | 1 | 20 | 4 | `flexible` | `medium` | `rebalance_layout` |
| `medium` | 4 | 2 | 18 | 5 | `support_only` | `medium` | `tighten_budget` |
| `high` | 6 | 2 | 16 | 4 | `support_only` | `low` | `table_or_microchart` |
| `dashboard` | 8 | 4 | 14 | 3 | `decorate_only` | `minimal` | `rollback_planning` |

### 冻结规则

- `density_label` 必须落在 outline 的 `密度下限 / 密度上限` 之间。
- `density_reason` 必须说明为什么这页最终落在该档，而不是空泛地写“内容较多”。
- `density_contract` 必须显式写出 `deck_bias`、`page_lower_bound`、`page_upper_bound`、`max_cards`、`max_charts`、`min_body_font_px`、`max_lines_per_card`、`image_policy`、`decoration_budget`、`overflow_strategy`。
- `dashboard` 只允许 `content` 页使用，且优先 `mixed-grid` / `t-shape`。
- `high / dashboard` 禁 `image_hero` 主卡，禁 `hero-background` 大图。

## Phase 4：`planningN.json` 结构合同（强制）

你的输出必须是**可直接被 `planning_validator.py` 校验的 JSON**。以下是 schema 骨架（**只展示结构，不展示设计决策** -- 布局、卡片类型、视觉风格全部由你自主决定）：

```json
{
  "page": {
    "slide_number": "<页码>",
    "page_type": "<cover/toc/section/content/end>",
    "narrative_role": "<叙事角色>",
    "title": "<页标题>",
    "page_goal": "<一句话核心论点>",
    "audience_takeaway": "<观众带走什么>",
    "visual_weight": "<1-10 信息密度>",
    "density_label": "<low/mid_low/medium/high/dashboard>",
    "density_reason": "<为什么这一页最终落在这个密度档>",
    "density_contract": {
      "deck_bias": "<relaxed/balanced/ultra_dense>",
      "page_lower_bound": "<来自 outline 的密度下限>",
      "page_upper_bound": "<来自 outline 的密度上限>",
      "max_cards": "<整数>",
      "max_charts": "<整数>",
      "min_body_font_px": "<整数>",
      "max_lines_per_card": "<整数>",
      "image_policy": "<flexible/support_only/decorate_only>",
      "decoration_budget": "<generous/medium/low/minimal>",
      "overflow_strategy": "<rebalance_layout/tighten_budget/table_or_microchart/rollback_planning>"
    },
    "layout_hint": "<你的布局选择>",
    "layout_variation_note": "<与上一页的结构对比（如果有微调），要求详尽>",
    "focus_zone": "<视觉焦点区域描述>",
    "negative_space_target": "<high/medium/low>",
    "page_text_strategy": "<文字策略>",
    "rhythm_action": "<推进/爆发/缓冲/收束>",
    "must_avoid": ["<你认为这页最危险的平庸设计陷阱>"],
    "variation_guardrails": {
      "same_gene_as_deck": "<哪些元素跨页保持统一>",
      "different_from_previous": ["<与上一页的具体变化维度>"]
    },
    "director_command": {
      "mood": "<你为这页设定的情绪基调>",
      "spatial_strategy": "<你的空间编排策略>",
      "anchor_treatment": "<你怎么处理视觉锚点>",
      "techniques": ["<你选用的技法编号>"],
      "prose": "<用电影镜头语言描述这页的视觉感受>"
    },
    "decoration_hints": {
      "background": {"feel": "<>", "restraint": "<>", "techniques": ["<>"]},
      "floating": {"feel": "<>", "restraint": "<>", "techniques": ["<>"]},
      "page_accent": {"feel": "<>", "restraint": "<>", "techniques": ["<>"]}
    },
    "source_guidance": {
      "brief_sections": ["<素材引用路径>"],
      "citation_expectation": "<引用策略>",
      "strictness": "<证据边界>"
    },
    "resources": {
      "page_template": "<null 或页面模板 ref>",
      "layout_refs": ["<你的 layout ref>"],
      "block_refs": [],
      "chart_refs": ["<你选用的 chart ref>"],
      "principle_refs": ["<你需要的设计原则>"],
      "resource_rationale": "<为什么选这些资源，必须说明理由>"
    },
    "cards": [
      {
        "card_id": "<s页码-role-序号>",
        "role": "<anchor/support/context>",
        "card_type": "<你的卡片类型选择>",
        "card_style": "<你的视觉变体选择>",
        "argument_role": "<claim/evidence/context>",
        "headline": "<精炼标题>",
        "body": ["<正文字符串数组>"],
        "data_points": [{"label": "<>", "value": "<>", "unit": "<>", "source": "<>"}],
        "chart": {"chart_type": "<你的图表类型>"},
        "content_budget": {"headline_max_chars": 12, "body_max_bullets": 3, "body_max_lines": 5},
        "image": {
          "mode": "<generate/provided/manual_slot/decorate>",
          "needed": "<true/false>",
          "usage": "<null 或图片用途>",
          "placement": "<null 或放置位置>",
          "content_description": "<null 或描述>",
          "source_hint": "<null 或路径>",
          "decorate_brief": "<装饰说明>"
        },
        "resource_ref": {"chart": "<>", "principle": "<>"}
      }
    ],
    "workflow_metadata": {
      "stage": "planning",
      "workflow_version": "2026.04.09-v4.1",
      "planning_schema_version": "4.1",
      "planning_packet_version": "4.1",
      "planning_continuity_version": "4.1"
    }
  }
}
```

> **重要提醒**：以上每个 `<>` 占位符最终都将落地为坚如磐石的代码。你需要如严密工程师一般，根据本页的内容、受众和物理界限出具精确的排版装配图。

### 必填字段与枚举底线

- 顶层页字段至少要有：`slide_number`、`page_type`、`title`、`page_goal`、`cards`、`visual_weight`、`density_label`、`density_reason`、`density_contract`、`director_command`、`decoration_hints`、`resources`、`workflow_metadata`。
- `page_type`：`cover` / `toc` / `section` / `content` / `end`
- `narrative_role`：与 outline 的叙事角色对齐，使用 `cover` / `toc` / `section` / `evidence` / `comparison` / `process` / `close` / `cta`
- `density_label`：`low` / `mid_low` / `medium` / `high` / `dashboard`
- `density_contract.image_policy`：`flexible` / `support_only` / `decorate_only`
- `density_contract.decoration_budget`：`generous` / `medium` / `low` / `minimal`
- `density_contract.overflow_strategy`：`rebalance_layout` / `tighten_budget` / `table_or_microchart` / `rollback_planning`
- 内容页必须有 `layout_hint`，并从 validator 认可的集合中选，如 `single-focus`、`symmetric`、`asymmetric`、`three-column`、`primary-secondary`、`hero-top`、`mixed-grid`、`l-shape`、`t-shape`、`waterfall`
- `cards[].role`：`anchor` / `support` / `context`
- `cards[].card_style`：`accent` / `elevated` / `filled` / `outline` / `glass` / `transparent`
- `cards[].body` 必须是**字符串数组**，不要写成单个字符串
- `cards[].data_points` 必须是对象数组；有数字时尽量带 `source`
- `cards[].content_budget` 必须是对象；哪怕是最小对象也要显式写出。它还必须服从页级 `density_contract`
- `cards[].image.needed = true` 时，`usage` / `placement` / `content_description` / `source_hint` 都必须填写；否则这些字段应为 `null`

### 密度专项底线

- `cards` 总数不得超过 `density_contract.max_cards`
- 有 `chart.chart_type` 的卡片数不得超过 `density_contract.max_charts`
- 每张卡的 `content_budget.body_max_lines` 不得超过 `density_contract.max_lines_per_card`
- `dashboard` 页不得使用 `image_hero` 卡片，不得把大图当主锚
- `dashboard` 页的 `image_policy` 必须是 `decorate_only`

---

## Phase 5：图片策略决策（必须明确，不得含糊）

| 模式 | 适用场景 | 必填字段 |
|------|---------|---------|
| `generate` | 封面页、章节页、需要强视觉冲击的核心页 | `image.needed=true`、`usage`、`placement`、`content_description`、`source_hint`（目标落盘路径）、`image.prompt`（英文图生图提示词） |
| `provided` | 用户已提供图片/品牌图库/截图 | `image.needed=true`、`source_hint`（真实本地路径）|
| `manual_slot` | 用户后续自己补图，先占位 | `image.needed=false`、`image.slot_note` 说明槽位位置、比例、替换建议 |
| `decorate` | 数据页、逻辑页、纯排版页 | `image.needed=false`、`image.decorate_brief` 说明内部视觉语言（SVG/渐变/色块/水印/字体装饰）|

**禁止留模棱两可的 mode。选定后不得在 HTML 阶段临时改变。**

**额外密度约束**：
- `low / mid_low`：可使用更自由的图片策略
- `medium`：图片只能做支撑，避免吞掉正文
- `high`：不得用 `hero-background`，图片只可做支撑或局部说明
- `dashboard`：默认 `decorate`，不得把大图当主锚

---

## Phase 6：你是架构师，纪律与创意并重

> **核心理念**：上面的 Phase 2 菜单、Phase 3 密度合同和 Phase 4 schema 不是让你随意发挥的草稿，而是你作为架构设计者定下的**硬性工程图纸**。真正的创意，是在极致严酷的约束条件内绽放的。

**绝对的执行纪律（The Execution Discipline）：**
- `layout_hint` **是界面的黄金承重墙**。在下游的渲染阶段，它将被**以不妥协的精确度**映射到真实的 DOM 网格结构上，不可随意打破原有的版面重心设定。
- `card_type` 和 `chart_type` 意味着**特定设计规范的强制降临**。选定了特定类型，就必须遵循其最佳实践，否则后续的图审环节将直接把页面打回重做。
- `director_command` 是你的图纸批注 —— 这是对空间利用的更高维度说明，指导下游在不破坏骨架的前提下，该着重把哪些 CSS 精工细作落实。图审也不会为你善后，必须指令严密。
- `must_avoid` 是致命红线 —— 每页至少写 1 条真正有意义的禁区，提醒自己在边界内做到最好，主动拒绝平庸妥协。

**图审警示**：你在此阶段定下的所有结构决策，都必须对最终代码全权负责。不要以为有“像素级图审”兜底就可以随意偏离框架，图审是用来打磨微调的，绝不是来擦屁股和重构骨架的。

---

## Phase 7：cards 字段填充规范

每张卡片必须包含：
- `card_id`：稳定唯一，建议 `s{页码}-{anchor|support|context}-{序号}`
- `role`：`anchor` / `support` / `context`
- `card_type`：validator 枚举值，如 `text` / `data` / `list` / `process` / `data_highlight` / `timeline` / `diagram` / `quote` / `comparison` / `people` / `image_hero` / `matrix_chart`
- `card_style`：6 种合法视觉变体之一
- `headline`：标题（精炼，不超过 12 字）
- `body`：正文字符串数组，不能为空
- **【反泄漏铁律】**：`headline` 和 `body` 里面**只能且必须**填写最终展示给观众看的内容文案！绝不准许把纲要里的“旁白说明”、“工作动作”、“排版大意”（例如：*“这一页先把整场内容压缩成地图，再看拆解”* 这种明显属于幕后解说的话）当成台词本填进去！所有面向设计的幕后说明请扔进 `director_command`，若将工作指导语暴露在卡片正文上将被视为重大设计事故！
- `data_points`：如有数值则填对象数组
- `content_budget`：内容预算对象，且必须服从页级 `density_contract`
- `image`：完整图片合同对象，带 `mode`
- `resource_ref`：需要定向绑定某个 block/chart/principle 时写这里
- `image.slot_note` / `image.decorate_brief` / `image.prompt`：按图片模式按需补充

可选但推荐：
- `argument_role`
- `chart`

**不得出现空 `body` 的卡片。**

---

## Phase 8：设计意图传递字段

在坚守骨架的基础上拔高呈现品质。请严格定义并使用以下字段，向 HTML 阶段下达你的精确工程指令与微雕方案，它们构成了后续视觉落地的强制合同：

- `focus_zone`：提议的主张和视觉焦点区域
- `must_avoid`：明确提配 HTML 阶段不要陷入的平庸模板化设计
- `director_command`：给出富有创意性的结构、锚点和高级技法方向
- `decoration_hints`：描述装饰强度与视觉层次
- `source_guidance`：约束证据边界与引用期望
- `resources` / `resource_ref`：推荐消费的组件资源

---

## Phase 9：自审（强制）

运行 `planning_validator.py`，直到零 ERROR：

```bash
python3 SKILL_DIR/scripts/planning_validator.py $(dirname PLANNING_OUTPUT) --refs REFS_DIR --page PAGE_NUM
```

- ERROR 必须全部修复才能 FINALIZE
- WARNING 建议修复，不强制
- 自审通过后立即发送 FINALIZE，然后等待 HTML 阶段指令
