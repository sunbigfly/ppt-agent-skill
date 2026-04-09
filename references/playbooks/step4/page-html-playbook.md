# Page HTML Playbook -- 单页 HTML 设计稿

## 目标

忠实还原 planning JSON 里的骨架与精神，运用 `resource_loader.py resolve` 的解析能力，将抽象组件组装成极具高级设计感的**单页自包含 HTML**。

---

## Phase 1：骨架理解（不得跳过）

读取 `planning{n}.json` 的以下字段作为本阶段的硬约束：

| 字段 | HTML 阶段的含义 |
|------|--------------|
| `page_type` / `layout_hint` | 决定整体骨架与页面自由度 |
| `density_label` / `density_contract` | 决定本页是高自由度还是低自由度执行模式 |
| `focus_zone` | 决定哪个卡片/区域应该有最大视觉权重 |
| `negative_space_target` | 决定留白比例（high=宽松 / medium=适中 / low=密集）|
| `cards[].role` / `cards[].card_style` | 决定主次顺序与卡片存在感 |
| `cards[].card_id` | 要在 HTML 中逐一落地，并映射到 `data-card-id` |
| `cards[].content_budget` | 限制每张卡片的承载量，防止溢出 |
| `director_command` / `decoration_hints` | 决定镜头感、装饰层次和实现边界 |
| `source_guidance` / `must_avoid` | 决定证据呈现方式与禁止动作 |
| `image.mode` | 严格按下面第 3 条执行 |

---

## Phase 2：资源正文消费（强制执行，不得跳过）

```bash
python3 SKILL_DIR/scripts/resource_loader.py resolve --refs-dir REFS_DIR --planning PLANNING_OUTPUT
```

脚本返回 planning 中引用的每个资源的**完整正文实现**，包含：
- 组件的 HTML 结构骨架（含 class 命名示例）
- 推荐的 CSS 参数（间距、字号、颜色变量用法）
- 数据格式要求（如 chart 的 data 格式）

**你必须将此作为不可逾越的底层骨架。基于此骨架，你可以运用高级的表达技巧（如 CSS 空间处理）增强它，但绝对禁止偏离或破坏原始结构的逻辑编排。图审只会拦截错误，不会为你重构错乱的骨架。**

特别注意：
- 虽然 resolve 提供了基础结构，但你必须**严格对齐原 `layout_hint` 所赋予的空间逻辑**。你可以用更现代、精细的 CSS 增强它，但绝不支持“摧毁重建”。
- 允许在极致对齐和还原规划骨架的前提下优化视觉，但不要妄图在此时挑战原本规划好的数据主次。
- `process` 这类没有独立 block 文件的 card_type，须用坚固的原生 DOM 结构结合严谨的布局技法将其承接，禁止随意破坏既定的阅读动线。

### 密度执行模式（必须服从）

- `low / mid_low`：高自由度，可使用更强的留白、图片和材质变化
- `medium`：中自由度，允许有设计表达，但不能破坏阅读秩序
- `high / dashboard`：低自由度，只能做稳态 grid / flex 骨架，优先表格、矩阵、微图表，禁止依赖复杂绝对定位硬塞内容

**特别红线**：
- `high / dashboard` 禁主视觉大图卡
- `dashboard` 禁大面积水印、禁装饰抢主阅读路径
- `density_contract` 是最高施工合同，HTML 不得自行抬高或降低本页密度

---

## Phase 3：图片模式严格执行

| image.mode | HTML 要做什么 | 绝对禁止 |
|-----------|-------------|---------|
| `generate` / `provided` | 用 `source_hint` 路径渲染 `<img src>` 或 `background-image: url()` | 不得用占位色块替代真实图 |
| `manual_slot` | 渲染明确尺寸的图片占位框（带虚线边框 + 文字说明"[图片替换位]"）| 不得删掉或做成看不出来的空白 |
| `decorate` | 使用内联 SVG、CSS 渐变、几何色块、大字水印、圆圈装饰等内部视觉语言补足氛围 | 不得留空白大洞，不得放空的 `<div>` |

同时严格服从 `density_contract.image_policy`：
- `flexible`：可自由选图，但仍须服务 page_goal
- `support_only`：图片只能做支撑，不得做整页背景大图
- `decorate_only`：不得渲染外部图片，只能 `decorate`

---

## Phase 4：卡片落地对账（强制）

- `planning.cards[]` 中的每一张卡都必须有一个对应的 HTML 根节点。
- 每个根节点都要带 `data-card-id="<card_id>"`，便于 Review 阶段与 planning 对账。
- `role = anchor` 的卡必须成为全页第一视觉落点；`support/context` 退后，但不能消失。
- 任何**纯装饰节点**都必须带 `data-decoration-layer="background|floating|page-accent"`，并同时写 `aria-hidden="true"`；`visual_qa.py` 会直接按这个标记统计装饰预算。
- 若卡片带 `chart.chart_type`，最终图表类型必须与 planning 保持一致；不要把 `comparison_bar` 偷换成普通 list。
- 若 `source_guidance` 要求保留来源，至少在卡片 footer / caption / 注释位中给出来源提示。
- 卡片数量、图表数量、每卡行数都不得超出 `density_contract` 的预算上限。
- **【反泄漏清扫防线】**：在你把 JSON 里的 `body` 和 `headline` 填入 HTML 标签时，如果读到了明显的**“旁白解说”、“排版动作”**（例如：“这一页先做铺垫，最后收束到结论”等废话），**绝对不准老实巴交地把它渲染在大屏幕上！** 这是前置 Planning 代理漏掉的导演指导语，你必须主动充当最后一道防火墙将其直接剔除，或自行将其改写为干货文案！

---

## Phase 5：画布物理红线（不可违反）

```css
* {
  box-sizing: border-box; /* 像素级排版防崩核心 */
}

body {
  width: 1280px;
  height: 720px;
  overflow: hidden;
  margin: 0;
  padding: 0;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale; /* 保障文字渲染精度 */
}
```

**像素级渲染安全防线（涉及无头浏览器最终出图质量，极度重要）：**
- **流体坍缩预防**：在高度自由发挥时，`flex` / `grid` 极易出现子项挤压坍缩。凡是重要卡片或必须撑开的区域，务必使用 `min-width`, `min-height` 或 `flex-shrink: 0`。
- **行高裁剪预防**：文字的 `line-height` 若低于 `1.3`，部分英文小写字母下端极其容易被隐形裁剪，正文需保持合理行高。
- **边框与阴影溢出**：所有的边框宽度、`box-shadow` 都可能溢出原有容器。借助于 `box-sizing: border-box`，确保 padding 和 border 在规划宽度内。
- **密度合同预防**：正文最小字号不得低于 `density_contract.min_body_font_px`；如果放不下，先减装饰，再收紧预算，再回退 planning，不得偷缩到不可读。

- **禁止** `width: 100%; height: 100%` 然后依赖父容器
- **禁止** `transform: scale()` 缩放 hack
- **禁止** 引用外部 CSS 文件（如 `common.css`、`deck.css`）

### 统一导航骨架（强制 -- 保证全 deck 视觉一致性）

每个页面由独立的 PageAgent 生成，**必须**使用统一的标题区和页脚区 HTML 骨架，避免拼装后各页标题/页脚形态各异。骨架规范详见 `design-specs.md` A 节「统一导航骨架合同」，核心规则如下：

| page_type | 标题区 | 页脚区 |
|-----------|--------|--------|
| `content` / `toc` | **强制** `header.slide-header > span.overline + h1.page-title`，`position:absolute; top:20px` | **强制** `footer.slide-footer`，`position:absolute; bottom:12px` |
| `section` | **自由**（章节标题是设计主角） | **强制** 同上 |
| `cover` / `end` | **自由** | **可选** |

**视觉创意不受影响**：overline 内容、page-title 字号、装饰线、页脚风格（W12 终端/印章/进度条）都可按风格变化。统一的只是 **HTML 结构和定位方式**。

---

## Phase 6：风格变量严格绑定

从 `style.json` 的 `css_variables` 提取所有变量，写入 HTML 的 `:root`：

```css
:root {
  --bg-primary: [从 style.json 取];
  --bg-secondary: [从 style.json 取];
  --card-bg-from: [从 style.json 取];
  --card-bg-to: [从 style.json 取];
  --card-border: [从 style.json 取];
  --card-radius: [从 style.json 取];
  --text-primary: [从 style.json 取];
  --text-secondary: [从 style.json 取];
  --accent-1: [从 style.json 取];
  --accent-2: [从 style.json 取];
  --accent-3: [从 style.json 取];
  --accent-4: [从 style.json 取];
  --font-primary: [从 style.json font_family 取];
}
```

- `design_soul`：用来校准情绪，不得直接抄成页面文案
- `variation_strategy`：控制这一页的变化幅度，避免与相邻页同构复制
- `decoration_dna.forbidden`：硬边界，违反即自动不达标
- `decoration_dna.recommended_combos`：优先采用
- `decoration_dna.signature_move`：跨页识别锚点，必须出现
- `density_contract.decoration_budget`：同时约束装饰层数量。默认上限建议为：`generous <= 6`、`medium <= 4`、`low <= 2`、`minimal <= 1`

---

## Phase 7：你是最顶级的架构执行者

> **核心理念**：planning JSON 是你的核心工程图纸，resource resolve 的组件正文是你的模具。你的工作是结合高精度的 CSS（阴影、滤镜、裁切），在绝对服从图纸尺寸和空间设定的前提下，雕琢出令人惊艳的最终渲染结果。

**你的架构底线与渲染特权：**
- **严守骨架**：绝不允许在宏观上摧毁 Planning 划定的 `layout_hint` 结构体系和文档重力场。
- **释放渲染力**：在确保结构坚如磐石的前提下，CSS 的实现特权完全下放给你。你可以大胆使用绝对定位、高级滤镜、复杂渐变、clip-path 去雕琢卡片，尽情通过 CSS 解放被原数据束缚的表现张力。
- **密度服从优先**：`high / dashboard` 页首先要清晰、稳定、可扫读，再谈戏剧化表现。不得为了“酷”牺牲结构。

**设计独立性自检（追问：我的执行是否精准且克制？）**：
- 本页的底层承重墙（DOM结构）与 `page_goal` 和 `director_command` 的原意做到了一比一还原吗？
- 视觉锚点的位置是否彻底捍卫了原设计稿中定义的信息主次？
- 严禁套模板的心理：不可直接拿通用结构的冗余代码应付了事，任何多余的包裹标签都是负面的。

**核心保障约束**：你是本次渲染过程的全权负责方。图审环节（Review）只是出厂前的最后一道质检防线，它不会替你收拾结构混乱的烂摊子，所有的错误都必须由你亲自修复。

---

## Phase 8：完成条件

写入目标 HTML 文件后：
- 文件非空
- 格式绝对纯净：HTML 中不得以可见文本形式包含大模型思考过程（如阴阳自检、摘要阐述、策略说明等与实际幻灯片不相关的文字）
- 无语法错误（HTML 标签闭合完整）
- 没有明显乱码或缺失的 CSS 变量引用
- `planning.cards[]` 全部能在 HTML 中找到对应的 `data-card-id`

发送 FINALIZE 信号，然后等待 Review 阶段指令。
