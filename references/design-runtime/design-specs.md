# 设计规格书（A/B/C/D/E -- 稳定参考，由 `scripts/resource_loader.py` 自动注入 GLOBAL_RESOURCES）

> 本文件包含画布规范、排版阶梯、卡片规则、色彩装饰、页面类型设计和输出规范。
> 内容稳定且不需要每次都在 LLM 上下文中占位，由 assembler 机械化注入。

---

## A. 画布与排版

### 画布规范（不可修改）

- 固定尺寸: width=1280px, height=720px, overflow=hidden
- 标题区: 左上 40px 边距, y=20~70, 最大高度 50px（cover/section/end 页可自由处理标题，不受此约束）
- 内容区: padding 40px, y 从 80px 起, 可用高度 580px, 可用宽度 1200px
- 页脚区: 底部 40px 边距内，高度 20px

### 统一导航骨架合同（所有页面强制执行）

**为什么需要统一骨架**：每个页面由独立的 PageAgent 生成，如果不统一标题区和页脚区的 HTML 结构，最终拼装出来的演示文稿会出现标题/页脚形态各异、位置飘忽的问题。以下骨架是跨全 deck 保持视觉一致性的最小合同。

#### 页面分类与骨架适用规则

| page_type | 标题区骨架 | 页脚区骨架 | 说明 |
|-----------|-----------|-----------|------|
| `content` | **强制使用**下方统一结构 | **强制使用**下方统一结构 | 正文页需要一致的导航体验 |
| `toc` | **强制使用** | **强制使用** | 目录页也需要标题和页脚 |
| `cover` | **自由处理**（标题是核心视觉事件） | **可选**（品牌信息可自由放置） | 封面标题是设计主角，不受骨架约束 |
| `section` | **自由处理**（章节标题是唯一主角） | **强制使用** | section 标题自由发挥，但页脚保持统一 |
| `end` | **自由处理** | **可选** | 结束页收束镜像，自由度高 |

#### 统一标题区 HTML 骨架（适用于 content / toc 页）

```html
<!-- 标题区：position:absolute 钉在画布顶部，所有 content/toc 页共用相同结构 -->
<header class="slide-header">
  <span class="overline">PART 0{{part_number}} &mdash; {{part_title}}</span>
  <h1 class="page-title">{{page_title}}</h1>
</header>
```

```css
.slide-header {
  position: absolute;
  top: 20px; left: 40px; right: 40px;
  height: 50px;
  display: flex;
  align-items: baseline;
  gap: 16px;
  z-index: 10;
}
.overline {
  font-size: 10px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--accent-1); opacity: 0.8;
  white-space: nowrap;
}
.page-title {
  font-size: 26px; font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  margin: 0;
}
```

> **创意自由空间**：overline 的内容（Part 编号/品牌标签/空白）、page-title 的具体字号和装饰线、标题与 overline 的位置关系，都允许按风格变化。但 **HTML 结构（`header.slide-header > span.overline + h1.page-title`）和定位方式（`position:absolute; top:20px`）必须全 deck 统一。**

#### 统一页脚区 HTML 骨架（适用于 content / toc / section 页）

```html
<!-- 页脚区：position:absolute 钉在画布底部，全 deck 统一结构 -->
<footer class="slide-footer">
  <span class="footer-section">{{section_label}}</span>
  <span class="footer-page">{{current_page}} / {{total_pages}}</span>
</footer>
```

```css
.slide-footer {
  position: absolute;
  bottom: 12px; left: 40px; right: 40px;
  height: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}
.footer-section {
  font-size: 10px; color: var(--text-secondary);
  opacity: 0.5; letter-spacing: 1px;
}
.footer-page {
  font-size: 10px; color: var(--text-secondary);
  opacity: 0.5;
}
```

> **创意自由空间**：页脚内容可以用叙事化页脚（W12 技法）替换 `.footer-section` 的显示内容（如终端状态栏、印章徽记、进度条），但 **HTML 结构（`footer.slide-footer`）和定位方式（`position:absolute; bottom:12px`）必须全 deck 统一。** style.json 的 `decoration_dna.signature_move` 如指定页脚风格，优先执行。

### 排版阶梯（拉开分层 -- 字号反差是设计力的核心指标）

| 层级 | 用途 | 字号 | 字重 | 行高 | 颜色 | 设计建议 |
|------|------|------|------|------|------|---------|
| H0 | 封面主标题 | 48-160px | 900 | 0.85-1.1 | --text-primary | 尽量让封面标题 >= 80px，奠定气场 |
| H1 | 页面主标题 | 26-32px | 700 | 1.2 | --text-primary | 推荐用渐变文字填充 |
| H2 | 卡片标题 | 16-20px | 700 | 1.3 | --text-primary | - |
| Body | 正文段落 | 13-14px | 400 | 1.8 | --text-secondary | - |
| Caption | 辅助标注 | 9-12px | 400 | 1.5 | --text-secondary, opacity 0.4-0.6 | - |
| Overline | PART 标识 | 10-12px | 700, letter-spacing: 2-4px | 1.0 | --accent-1 | 推荐给内容页加上 overline，提升空间层次 |
| Data-Hero | **核心 KPI（视觉锚点）** | **64-120px** | 900 | 0.85-1.0 | --accent-1 | **建议在数据页设置至少一个 64px+ 的超级数字** |
| Data-Sub | 辅助指标 | 28-40px | 800 | 1.0 | --accent-2/--accent-4 | 辅助数据应该拉开与核心 KPI 的大小反差 |

> **字号反差的极佳张力点**：建议每页最大字号与最小字号的**倍数比最好 >= 5 倍**。

### 间距是情绪变量（至少 2 种不同间距/页）

| 内容关系 | 间距 |
|---------|------|
| 数字 + 注解（紧密共生） | gap:2-4px |
| 同组卡片之间 | gap:16-20px |
| 不同主题区域 | gap:32-48px |
| 核心论点孤立 | padding:48-80px |

### 布局层级：《阴阳割线》下的绝对纪律与无限自由

> **核心哲学（阴阳割线法则）**：戴着不可打破的镣铐起舞，才是顶级的工业美学大师。
> - **阴极（不可妥协的物理枷锁）**：底层 DOM 容器、标准化 Header/Footer 以及 CSS Grid/Flex 的核心轨道是这个楚门世界的承重墙，绝对不可违逆。
> - **阳极（放飞极限的美学特权）**：只要没把承重墙碰倒，在这些区块内部你拥有无上的美术张力支配权。Typography字号的爆裂反差、重叠错位的透明层板、充满压迫感的负留白，请尽情粉碎那些令人作呕的“公文排版盒子”结构！

1. **骨架是强力的物理维度** -- `layout_hint` 约束了重力分布与页面组件的空间次序，你可以选择绝佳的实现技术（Grid/Absolute），但最终结构必须服从这套骨架体系。
2. **在枷锁内极力制造张力** -- 虽然骨架底盘可能居中对称，视觉表现上请大胆引入非对称的单侧浓重阴影、大跨度的夸张字号阶梯以及超大的图形色块，强制撕扯出画面的主次反差。
3. **消除盒子感的激进越界** -- 打破视觉边界时，绝不能通过摧毁 DOM 的嵌套层级来实现，必须利用子元素的负边距（margin-top: -30px）、底纹穿透融合以及大面积的毛玻璃羽化去解构这股呆板感！
4. **不同页面的结构收紧与视觉释放**：
   - **封面/章节/结束页**：极其森严的 Absolute 坐标系 + **极其放肆的超大字号和无底线的深邃景深**。
   - **数据密集页**：极其死板的 Grid 卡片阵列 + **极度嚣张且不受框约束的超级 KPI 数字浮动**。
   - **叙事页**：Flex 基石之上 + 充满故事感的图文不羁叠压。

#### 消除盒子感的合法手段（内部视觉暴动）

> **坚守的底线与放开的特权**：卡片**具体文本内容**不可溢出造成灾难（使用 `overflow:hidden` 和 `line-clamp` 截断）。但是卡片**包装自身**（装饰、底图、边缘）可以随意打破排印的安全距离、倾斜对撞、甚至互相刺穿拼接。你是视觉画板上不妥协的暴君。

**鼓励使用的破界级表现武器**：

```css
/* 负 margin 叠压 */ .card-overlap { margin-top: -20px; position: relative; z-index: 3; }
/* 出血定位 */ .bleed-element { position: absolute; left: -40px; width: calc(100% + 80px); }
/* 斜切裁剪 */ .card-sliced { clip-path: polygon(0 0, 100% 0, 100% 90%, 0 100%); }
/* 绝对定位 */ .card-free { position: absolute; top: 120px; left: 60px; width: 480px; }
/* 跨区域装饰 */ .deco-cross { position: absolute; z-index: 5; pointer-events: none; }
/* 背景色融合 */ .card-merged { background: transparent; border-right: 1px solid var(--card-border); }
```

**模板驱动设计的信号（说明设计者在套模板，而非为内容做设计）**：
- 连续多页的布局骨架完全相同（布局应该由内容驱动，而不是由习惯驱动）
- 所有内容页的视觉结构都是"标题 + N 个等大卡片排列" -- 这不是设计，是 Word 文档
- 每页的卡片都用相同的圆角、内边距、阴影 -- 说明设计者在复制粘贴而非思考
- 没有任何元素的空间位置反映了内容的主次关系

### 五层景深架构

| 层 | z-index | 内容 | 典型 CSS |
|----|---------|------|----------|
| **L0 背景层** | 0 | 背景色/渐变/氛围底图 | `background`, `background-image` |
| **L1 装饰底纹层** | 1 | 破界水印(T1)、底纹穿透(T6) | `position:absolute`, opacity 0.03-0.08 |
| **L2 内容承载层** | 2 | 卡片主体 | Grid 主要子元素 |
| **L3 强调浮层** | 3 | elevated/accent 卡片 | `box-shadow`, `transform:translateY(-4px)` |
| **L4 焦点层** | 4 | 超大数据数字(T2)、脉冲锚点(T9) | `position:relative; z-index:4` |

每页至少激活 3 层。

### 构图锚点与视觉动线

| 动线 | 适用页面 | 核心构图手段 |
|------|---------|-------------|
| **Z 型** | 标准内容页 | 左上标题 -> 右上数据 -> 左下论据 -> 右下结论 |
| **F 型** | 列表/文字密集页 | 标题横扫 -> 纵向快速扫描 |
| **焦点放射** | 单一数据/金句页 | 焦点居中或偏心，装饰从焦点向外扩散 |

**三分法锚点**：4 个交叉点（约 427,240 / 853,240 / 427,480 / 853,480）是视觉强点。画布正中央是最无聊的位置。

### 留白与视觉焦点

| 页面类型 | 内容填充率 |
|---------|-----------|
| 封面页 | 40-55% |
| 章节封面 | 25-40% |
| 标准内容 | 60-75% |
| 数据密集 | 70-80% |
| 结束页 | 35-50% |

---

## B. 内容与卡片

### 基础卡片灵动化建议

不要让卡片长得像标准公文块。

- **text（文本块）**：如果文字多，不要平铺直叙。提取一个最抓眼球的词加粗，或者在首字母使用类似杂志排版的 Drop Cap 首字下沉。
- **data（数据块）**：避免仅仅是“图表+图例”。把结论性的一句话作为最大字号，图表只是静静铺在下方作为背景。
- **list（列表块）**：放弃传统的无序列表点。可以用大号半透明数字、递进颜色的虚线色块，甚至让每条 list 项在绝对定位下稍微错位。
- **tag_cloud（标签云）**：不要把标签排成一个等间距的矩阵。让重要的标签很大，不重要的标签若隐若现。

### 卡片视觉变体（card_style）

- **追求层次反差**：一页至少 2 种 card_style
- `accent`：视觉爆裂点，通常一页 1 个
- `transparent`：推荐给复合组件（timeline/diagram/quote）
- `elevated`：悬浮锚点，多层阴影
- `filled`/`outline`/`glass`：自由搭配

### 微细节武器库（避免同质化）

如何让卡片显得精致而不是粗糙拼凑？

- **突破硬边**：用渐变模糊的线代替生硬的 solid border。 
- **点缀元素**：在卡片边缘加上类似 UI 界面角标的 10px 极小文字，标示出“来源”或“权重”。
- **异构高亮**：对重要词汇不要只用粗体，尝试加上一个 accent 颜色的底色药丸甚至波浪线。

**极简法则**：极致的留白与绝对的对齐，本身就是一种极具张力的高级细节，不要去一页里强行堆砌花里胡哨的特效。

### 元素韵律

| 节奏模式 | 适用场景 |
|---------|---------|
| **主副** | 1 个核心 + 2-3 个辅助，核心占 2fr |
| **递减** | 重要性递减，第一张跨 2 列 |
| **交错** | 等重要但需节奏感 |
| **孤岛+群落** | 核心独占 40-60%，辅助群紧密排列 |

**避免均等**：不要让所有卡片等宽等高排成一行。

---

## C. 色彩与装饰

### 60-30-10 色彩节奏

| 比例 | 角色 | 应用范围 |
|------|------|---------|
| 60% | 主色（背景） | --bg-primary |
| 30% | 辅色（内容区） | --card-bg-from/to |
| 10% | 强调色（点缀） | --accent-1 ~ --accent-4 |

> accent 色同页 1-2 种效果最佳。多色需求（如 tag_cloud）可灵活使用 accent-1 到 accent-4。

### 装饰元素

每页 2-3 种装饰。来源于策划稿 `decoration_hints` 三维度。

### 导航体系（统一骨架 + 风格自由）

底部辅助信息（章节、页码、品牌）的 **HTML 结构和定位必须使用 A 节定义的统一页脚区骨架**（`footer.slide-footer`），但骨架内部的**视觉风格**可多样化：叙事化页脚（W12 终端状态栏/印章/进度条）、极小微文字、accent 色强调等。风格变化通过替换 `.footer-section` 内容和修改字体/颜色/opacity 实现，不改变骨架结构。

### 渐变使用指引

- 同一页渐变方向保持和谐
- 渐变色彩从 CSS 变量取值

### 色彩与可读性

- 正文文字与背景对比度保持可读
- accent 色优先用于标题/标签/数据，不用于大段正文
- 颜色优先通过 `var(--xxx)` 引用

### 特殊字符

温度用 `°C`，化学式用 `<sub>`/`<sup>`，微米用 `μm`。

---

## D. 页面类型高级意境意图（通过强代码实现）

以下高级意境展示并非肆意发散，而是当策划下达了极其强烈的表达指令（如：空间压迫、无尽景深、极端收束）时，你可以采用的重度前端工程手段。实施它们的前提是必须稳固底层盒模型并精确计算坐标，禁止因为“追求特异效果”导致排版崩坏：

### 封面页的张力
- 尝试放弃居中。让标题紧贴左侧出血线，甚至超大字号（160px）直接跨越两行。
- 尝试“深不见底”的景深：背景不仅是颜色，还可以是一个巨大的品牌 Icon 水印，或者一段若隐若现的代码。

### 目录与过渡（章节）
- 章节页尝试 70%+ 的极端留白。标题极度偏心。
- 尝试把大纲编号当做图案来用：极大的数字（如 120px），极低的透明度（0.04），铺满整个侧边。

### 数据密集与仪表盘
- 不要把所有数据都装在盒子里。尝试让核心 KPI "脱框"（完全没有背景色和边框的隔离），直接 120px 裸露在画面中。
- 给次要数据极大的收缩度（28px 的次要字号与 120px 的脱框字号形成强反差）。

### 对比分析与选择
- 打破左右对称或并排罗列。推荐方案可以像一块巨石一样“隆起”（多层阴影、强光晕），而被弃方案像影子一样蜷伏在底部。
- 中间不需要画一条竖线，可以用对角线的渐变色带劈斩开两侧的空间。

### 引言与叙事
- 把引言当做艺术品，放入一整个空白屏幕的正中央，再丢下极低的透明度作为回声。

### 结束页
- 不要简单写“谢谢”。它可以是封面的收束镜像：同样的色调和构图，元素从极端的张扬变成极端的克制。

---

## E. 输出规范

### HTML 骨架参考

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<title>Slide {NN} - {TITLE}</title>
<style>
:root { /* 从 style.json 展开完整 CSS 变量 */ }
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
body {
  width:1280px; height:720px; overflow:hidden;
  background: var(--bg-primary);
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  position:relative; color:var(--text-primary);
}
</style>
</head>
<body>
<!-- 统一标题区（content/toc 页强制；cover/section/end 页按 A 节规则自由处理） -->
<header class="slide-header">
  <span class="overline">PART 01 &mdash; 章节标题</span>
  <h1 class="page-title">页面标题</h1>
</header>

<!-- 内容区从这里开始 -->

<!-- 统一页脚区（content/toc/section 页强制；cover/end 页可选） -->
<footer class="slide-footer">
  <span class="footer-section">章节标签</span>
  <span class="footer-page">3 / 12</span>
</footer>
</body>
</html>
```

### 隐形物理法则（5 条技术红线）

| # | 物理法则 | 设计意义 |
|---|--------|------|
| 1 | 1280x720px 画布，`body overflow:hidden` | 画布边界即视口 |
| 2 | 全局 `font-family` 统一 | 秩序的基石 |
| 3 | 全局依赖 CSS 变量 | 色彩锁定同一宇宙 |
| 4 | 容器内文字不溢出（`overflow:hidden` + `line-clamp`） | 容器壳可随意移动叠压 |
| 5 | 只使用纯静态视觉（无 `@keyframes`/`animation`/`transition`） | PPTX 导出不支持动画 |

### CSS 能力释放

可自由使用：`background-clip:text` / `clip-path` / `mask-image` / `conic-gradient` / `backdrop-filter` / `mix-blend-mode` / 多层 `box-shadow` / 伪元素 / `writing-mode` / `filter`。禁止 `@keyframes`/`animation`/`transition`。

### 设计倾向

| 平庸倾向 | 更好的选择 |
|---------|-----------|
| 标题 `text-align:center` | 偏心定位 + 装饰线 |
| 所有卡片同 padding | 核心更大，辅助更紧凑 |
| 全页 `flex; center; center` | 三分法偏心 + 对角线张力 |
| 所有卡片等大等高 | 主副节奏 / 递减 / 孤岛+群落 |
| 只用 1 层 box-shadow | 3-4 层渐进阴影 |
