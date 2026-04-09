# Stage 1: Page Planning -- 第 {{PAGE_NUM}} 页（共 {{TOTAL_PAGES}} 页）

> **【系统级强制指令 / CRITICAL OVERRIDE】**
> 本 prompt 已包含了你在此阶段所需的**全部**任务目标与 Playbook 细则。
> **严格禁止调用工具去读取外层的 `SKILL.md` 或主控全局规则文件！**
>
> 本阶段的唯一目标：产出 `{{PLANNING_OUTPUT}}`。作为架构师，你需要在这里定下不可逾越的**硬性工程图纸**。请在 `layout_hint`、`focus_zone` 和 `must_avoid` 等字段中施加严密的结构控制。后续的 HTML 阶段和图审环节，都将绝对服从你在此刻定下的框架纪律。
> 若外层 orchestrator 已提供阶段推进协议，则外层协议优先于本 prompt 中的完成信号描述。

这是你为第 {{PAGE_NUM}} 页执行的**第一阶段核心任务**：策划定骨稿。
你暂时不要写 HTML 代码，全力填好并校验 `{{PLANNING_OUTPUT}}`。

---

## Playbook（执行细则）

{{PLAYBOOK}}

---

## Design Principles Quick Reference

{{PRINCIPLES_CHEATSHEET}}

---

## 任务包

| 项目 | 路径/值 |
|------|--------|
| 页码 | {{PAGE_NUM}} / {{TOTAL_PAGES}} |
| 需求 | `{{REQUIREMENTS_PATH}}` |
| 大纲 | `{{OUTLINE_PATH}}` |
| 素材 | `{{BRIEF_PATH}}` |
| 风格 | `{{STYLE_PATH}}` |
| 图片素材目录 | `{{IMAGES_DIR}}` |
| 图片清单快照 | `{{IMAGE_INVENTORY_PATH}}` |
| 菜单快照 | `{{RESOURCE_MENU_PATH}}` |
| 运行日志 | `{{SUBAGENT_LOG_PATH}}` |
| SKILL 目录 | `{{SKILL_DIR}}` |
| 资源目录 | `{{REFS_DIR}}` |

---

## 产物路径

- 策划稿 JSON：`{{PLANNING_OUTPUT}}`
- Runtime 备份：`{{PLANNING_RUNTIME_COPY_PATH}}`
- Validator 报告：`{{PLANNING_VALIDATOR_REPORT_PATH}}`
- 文件内容必须是**纯 JSON 对象**（可直接写对象，也可包在 ```json fenced block 中），不要夹杂说明性 prose。

---

## 执行链路（固定顺序，不得跳步）

1. 读取 `{{OUTLINE_PATH}}` 中第 {{PAGE_NUM}} 页的定义（只关注你这一页），特别提取 `密度下限 / 密度目标 / 密度上限 / 节奏动作 / 信息姿态 / 锚点类型`
2. 深度读取 `{{REQUIREMENTS_PATH}}`，将其中的【受众画像】、【目标动作】和【版面心智】作为单页选型和内容设计的最高约束（例如：对底层技术受众放大图表卡片，对合作方主打对比及成果锚点）。
3. 读取 `{{BRIEF_PATH}}` 获取可用素材
4. 读取 `{{STYLE_PATH}}` 提取 `mood_keywords`、`variation_strategy`、`decoration_dna` 做情绪定调
5. 读取主链已生成的**图片清单快照** `{{IMAGE_INVENTORY_PATH}}`。
6. 如需刷新这份图片清单，再执行：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py run --log {{SUBAGENT_LOG_PATH}} --label planning-refresh-images -- \
     python3 {{SKILL_DIR}}/scripts/resource_loader.py images --images-dir {{IMAGES_DIR}} --output {{IMAGE_INVENTORY_PATH}}
   ```
7. 读取主链已生成的**组件/图表菜单快照** `{{RESOURCE_MENU_PATH}}`（这是给 runtime 留档的备份，也作为你本阶段优先使用的菜单视图）。
8. 如需刷新这份菜单快照，再执行：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py run --log {{SUBAGENT_LOG_PATH}} --label planning-refresh-menu -- \
     python3 {{SKILL_DIR}}/scripts/resource_loader.py menu --refs-dir {{REFS_DIR}} --output {{RESOURCE_MENU_PATH}}
   ```
9. **先冻结密度合同，再回答设计提问**。你必须先确定 `density_label`、`density_reason` 和 `density_contract`，再决定 `page_type`、`layout_hint`、`cards[].card_type`、`chart.chart_type`、`resource_ref`、`image.mode`、排版策略等。

### 设计决策驱动提问

在确定布局和资源之前，先回答这 4 个问题（可在心中推演，不需要写入产物）：

1. **观众在这一页应该先看到什么？** → 决定视觉锚点和主次关系
2. **这一页的信息是怎么"流动"的？** → 决定空间布局和视觉动线
3. **这一页和上一页的视觉感受应该有什么不同？** → 决定节奏变化
4. **在菜单中的工具里，哪些能最好地服务上面 3 个答案？** → 决定 layout_hint、card_type、chart、resource_ref

> **重要**：菜单里的工具依然是你的调色盘。同样的数据可以用完全不同的工具和布局来表达，关键是你想让观众产生什么感受。设计原则参考文件与映射表是你绝好的灵感索引，你完全可以跨界混搭布局。
> **唯一不可妥协的底线**：你可以自由构思并调配这些高级元素，但你的产物必须是精密计算后的产物！任何 `layout_hint` 或组件调用的选择，在下游环节都必须用符合其核心语义的底层结构去精确承接。你的奇思妙想不能以牺牲布局崩塌为代价。
> **密度红线**：`density_label` 只能落在 outline 给你的窗口里。`dashboard` 只允许 `content` 页，且必须同时把 `image_policy` 锁成 `decorate_only`。

**填写 `resources` 字段时必须说明选择理由**（推荐写入 `resources.resource_rationale`），例如回答"为什么用这个布局/组件能最好地让观众产生我想要的感受"。
10. 将完整 planning 写入 `{{PLANNING_OUTPUT}}`，并同步备份到 `{{PLANNING_RUNTIME_COPY_PATH}}`：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py run --log {{SUBAGENT_LOG_PATH}} --label planning-runtime-copy -- \
     cp {{PLANNING_OUTPUT}} {{PLANNING_RUNTIME_COPY_PATH}}
   ```
11. 自审（必须执行，不得跳过）：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py run --log {{SUBAGENT_LOG_PATH}} --label planning-validator -- \
     python3 {{SKILL_DIR}}/scripts/planning_validator.py $(dirname {{PLANNING_OUTPUT}}) --refs {{REFS_DIR}} --page {{PAGE_NUM}} --report {{PLANNING_VALIDATOR_REPORT_PATH}}
   ```
12. 修复所有 ERROR（WARNING 建议修复）。
13. 完成信号：输出 `--- STAGE 1 COMPLETE: {{PLANNING_OUTPUT}} ---`，然后按外层 orchestrator 协议继续下一阶段
14. 不要把当前阶段的完成信号误当作整页任务结束。

---

## 阶段边界

- 本阶段：只写 planning JSON，不写 HTML
- 下一阶段：orchestrator 会指引你进入 HTML 生成
- 消费规则：planning 阶段只读资源的 `> 引用层`（菜单），HTML 阶段才读正文层
