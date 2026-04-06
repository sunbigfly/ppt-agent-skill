# Stage 2: Page HTML Production -- 第 {{PAGE_NUM}} 页（共 {{TOTAL_PAGES}} 页）

> **【系统级强制指令 / CRITICAL OVERRIDE】**
> 本 prompt 已包含了你在此阶段所需的**全部**任务目标与 Playbook 细则。
> **严格禁止调用工具去读取外层的 `SKILL.md` 或主控全局规则文件！**
>
> **前置条件**：Planning 阶段已完成，`{{PLANNING_OUTPUT}}` 已就绪。
> 本阶段的唯一目标：基于 planning JSON 产出 `{{SLIDE_OUTPUT}}`。完成后发送 FINALIZE 信号。
> 若外层 orchestrator 已提供阶段推进协议，则外层协议优先于本 prompt 中的完成信号描述。

这是你为第 {{PAGE_NUM}} 页执行的**第二阶段核心任务**：HTML 设计稿生成。
你的策划稿（`{{PLANNING_OUTPUT}}`）是本阶段的主要输入，严格忠实还原其骨架。

---

## Playbook（执行细则）

{{PLAYBOOK}}

---

## 任务包

| 项目 | 路径/值 |
|------|--------|
| 页码 | {{PAGE_NUM}} / {{TOTAL_PAGES}} |
| 策划稿 | `{{PLANNING_OUTPUT}}` |
| 风格规范 | `{{STYLE_PATH}}` |
| 输出 HTML | `{{SLIDE_OUTPUT}}` |
| SKILL 目录 | `{{SKILL_DIR}}` |
| 资源目录 | `{{REFS_DIR}}` |
| 图片素材目录 | `{{IMAGES_DIR}}` |

---

## 执行链路（固定顺序，不得跳步）

1. 读取 `{{PLANNING_OUTPUT}}`，提取完整骨架（`page_type`、`layout_hint`、`focus_zone`、`negative_space_target`、`cards[].card_id/role/card_type/card_style/headline/body/data_points/chart/image/resource_ref`、`director_command`、`decoration_hints`、`source_guidance`、`resources`、`must_avoid`）
2. 读取 `{{STYLE_PATH}}`，提取 `css_variables`、`font_family`、`design_soul`、`variation_strategy`、`decoration_dna`
3. **必须执行** —— 获取 planning 引用资源的**正文层实现细节**（不能跳过，里面有组件级 CSS 参数和骨架建议）：
   ```bash
   python3 {{SKILL_DIR}}/scripts/resource_loader.py resolve --refs-dir {{REFS_DIR}} --planning {{PLANNING_OUTPUT}}
   ```
   resolve 输出的组件正文是必须严格遵从的起点。你是最严格的设计执行官 -- 在保证 1280x720 画布物理红线的前提下，结合 `page_goal` 和 `director_command`，运用高精度的代码将策划稿在 DOM 树中毫无妥协地还原。图审只会挑出你的瑕疵，不会容忍你重构骨架。
4. 核对图片素材，确认 `image.source_hint` 路径可访问：
   ```bash
   python3 {{SKILL_DIR}}/scripts/resource_loader.py images --images-dir {{IMAGES_DIR}}
   ```
5. **执行摘要（必须先写再动手）**——用 3 句话总结本页的核心策略，输出到对话中后再开始写 HTML：
   - 第 1 句：本页的核心论点和视觉焦点是什么
   - 第 2 句：使用什么布局结构和主要组件
   - 第 3 句：风格锚点（design_soul 如何体现在这一页）
6. 按以下**画布物理红线**生成自包含 HTML（不可违反）：
   - `body { width: 1280px; height: 720px; overflow: hidden; }` —— 不得写 100% 或其他尺寸
   - 禁止 `transform: scale()` 缩放 hack
   - 所有 CSS 内联在 `<style>` 标签中，禁止引用外部 CSS 文件
   - 字体从 `style.json` 的 `font_family` 取值，通过 Google Fonts 或系统字体栈引入
7. 按 `image.mode` 处理图片（**mode 在 planning 阶段已锁定，此处不得临时变更**）：
   - `generate` / `provided`（`image.needed=true`）：将 `source_hint` 路径绑定到 `<img src>` 或 `background-image`，图片必须实际渲染
   - `manual_slot`（`image.needed=false`）：渲染明确可替换的图片占位区（带边框/提示文字），不得偷偷删除占位区
   - `decorate`（`image.needed=false`）：不使用外部图片，用内联 SVG、色块、渐变、字体装饰补足视觉氛围，不得留空白大洞
8. **设计《阴阳割线》自检（写 HTML 前必须在心中回答并执行）**：
   - **阴极（不可抗拒的物理法则）**：本页底层承重墙符合 `page_goal` 和 `director_command` 所强制要求的结构吗？是否私自修改了顶部标题栏绝对锚点或改变了 Grid 流？（如是，则推翻重写！）
   - **阳极（极端爆裂的视觉特权）**：你的画面层次够深邃吗？是否在不触碰承重墙的前提下，使用了令人震颤的超大暗纹水印、负边距交叠对撞、以及字号达到 5 倍以上差距的极致排印技术，消除了死板的公文盒子感？
   - 证明你不仅是严谨的码农，更是狂热的前卫排印大师！
9. **每个 planning card 都必须在 HTML 中有对应渲染根节点**，并为根节点补上 `data-card-id="<planning.card_id>"` 便于 review 对账；如果某卡含 `chart.chart_type`，渲染结果必须与该类型匹配。
10. 将完整 HTML 写入 `{{SLIDE_OUTPUT}}`
11. 完成信号：输出 `--- STAGE 2 COMPLETE: {{SLIDE_OUTPUT}} ---`，然后按外层 orchestrator 协议继续下一阶段

---

## 阶段边界

- 本阶段：只写 HTML，不截图，不做 QA
- 下一阶段：orchestrator 会指引你进入 Review 图审
- 资源消费规则：本阶段读资源**正文层**（步骤 3），而非 planning 阶段用过的菜单摘要层
