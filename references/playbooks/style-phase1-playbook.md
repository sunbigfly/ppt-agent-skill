# Style Phase 1 Playbook -- 风格合同的定义与输出

## 目标

基于用户需求、大纲结构和 runtime 风格规则，输出一份可被 planning/html 稳定消费的 `style.json` 全局风格合同，而不是任何单页的 HTML 代码。

---

## 阶段执行流程

### Phase 1: 提炼风格约束

1. 读取 `requirements-interview.txt`
2. 抽取高优先级信号：品牌色、品牌禁区、受众、正式度、语言、配图策略。绝不允许在不知情的情况下选错受众（如给技术向听众做可爱风）。
3. 读取大纲 `outline.txt`
4. 判断整套 deck 的节奏类型：稳态推进 / 波浪起伏 / 发布会式冲刺 / 培训式均匀展开，以决定你的变化策略基调。

### Phase 2: 创造核心风格调色盘（拒绝机械查表）

不要做生搬硬套的“填表员”！**用户的需求（风格、受众、场景）拥有绝对的第一优先级！**

**决策你的核心风格取向：**
1. **深度提炼用户采访需求**：优先读取 `requirements-interview.txt` 中归一化后的 `style`、`brand`、`audience`；若文件保留 canonical 字段，也要同时对齐 `visual_style`、`brand_constraints`、`core_audience` 的含义。
2. **高级动态调色盘**：摆脱老土的死板色彩。凭借你的高级审美，构建一整套逻辑自洽的 12 个关键 `css_variables`（主背景色、卡片梯度、4个 accent 强调色）。
3. **只在极度迷茫时，才参考预置文件**。
如果用户要求“神秘东方”、“末日废土”、或者“社区极客感”，**你可以为其量身定做色彩搭配。但是，任何原创配色必须秉持至高无上的 Web 视觉安全原则！底色必须低频或静谧，文字绝不允许丢失强烈的对比度可读性。严禁为了追求“特立独行”搭配出导致阅读瞎眼的乱色！**

哪怕用户需求罕见如“神秘东方”、“孟菲斯几何”、“末日废土”或者“技术社区感”，**也必须将它们的高级感封装在严苛的系统变量矩阵中！**。千万不要以“创意”为名配出违背美学法则的泥石流色组。用户的 `style` / `visual_style` 需求指南针拥有第一地位，而你的产出必须符合 Token 纪律与大厂视觉审美红线。

### Phase 3: 生成 style.json 合同

你必须输出一份严格遵守下列字段要求的 JSON 合同文件：

*   `style_id` / `style_name`
*   `mood_keywords`：**（强制：必须提供 3-5 个关键词的数组）**
*   `design_soul`：描述整套 deck 的设计目标，**绝对不可以**写成某一页的成品描述或构图指导。
*   `variation_strategy`：必须同时说明“哪些元素允许变”和“哪些元素锁死不动”。不能写成逐页执行指令。
*   `decoration_dna.signature_move`：必须有，且为非空字符串。
*   `decoration_dna.forbidden`：**（强制：必须提供 2-5 个元素的数组）**
*   `decoration_dna.recommended_combos`：**（强制：必须提供 2-4 个元素的数组）**
*   `font_family`

#### css_variables 键命名与数量规范（强制红线）

这 12 个变量是基石，必须定义并且键名**不能更改一个字母**：

```json
{
  "bg_primary": "#...",
  "bg_secondary": "#...",
  "card_bg_from": "#...",
  "card_bg_to": "#...",
  "card_border": "#...",
  "card_radius": "...px",
  "text_primary": "#...",
  "text_secondary": "#...",
  "accent_1": "#...",
  "accent_2": "#...",
  "accent_3": "#...",
  "accent_4": "#...",
  "css_snippets": {
    "example_class": "font-weight: 700;"
  }
}
```

- key 必须使用下划线（无 `--` 前缀），对应校验合同要求。
- 必须严格保留这 12 个基础变量名，禁止改名。如需自定义增加可以增加，但这 12 个不可少。
- `css_snippets` 必须是对象 (Object)，格式为 `"键名": "值"`，**绝对不能是数组 (Array)！** 确有必要时可用它固化跨页重复的局部样式结构（如阴影），但绝对不能包含能驱动整页骨架布局的 CSS。
