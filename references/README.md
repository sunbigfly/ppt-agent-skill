# References Index

本目录包含 PPT 工作流的资源真源。主控制台通过 `prompt_harness.py` 定向注入 playbook / runtime 规则；页面阶段再由 `resource_loader.py` 动态加载版式、组件与图表正文。

## 目录结构

```
references/
  playbooks/          -- subagent 执行细则（5 个 + step4/ 下 3 个）
  prompts/            -- prompt 模板（多个 tpl-*.md + 2 个 module-*.md + step4/ 下 4 个）
  layouts/            -- 版式资源（10 种）
  blocks/             -- 区域展示组件（8 种 + card-styles）
  charts/             -- 图表组件（13 种 + runtime-chart-rules）
  styles/             -- 风格主题（8 种 + runtime-style-rules + runtime-style-palette-index）
  principles/         -- 设计原则（7 种 + runtime-failure-modes）
  page-templates/     -- 页面结构模板（cover/toc/section/end）
  design-runtime/     -- 数据类型映射 + 设计规格 + CSS 武器库
```

## 核心入口

先读这些，再看资源库细项：

1. `SKILL.md` -- 主控制台合同：状态机、统一调度骨架、Gate、恢复规则
2. `playbooks/research-phase{1,2}-playbook.md` -- Step 2A 搜集整理执行细则与审查
3. `playbooks/source-phase{1,2}-playbook.md` -- Step 2B 资料整合执行细则与审查
4. `playbooks/outline-phase{1,2}-playbook.md` -- Step 3 大纲编写与自审执行细则
5. `playbooks/style-phase{1,2}-playbook.md` -- Step 3.5 全局风格合同与字段自审
7. `playbooks/step4/page-planning-playbook.md` -- Step 4A 页面规划执行细则
8. `playbooks/step4/page-html-playbook.md` -- Step 4B HTML 落地执行细则
9. `playbooks/step4/page-review-playbook.md` -- Step 4C 图审修复执行细则
10. `styles/runtime-style-rules.md` -- Step 3.5 runtime 风格字段合同
11. `styles/runtime-style-palette-index.md` -- Step 3.5 预置风格基底入口

## Prompt 模板

`tpl-*.md` 文件由 `scripts/prompt_harness.py` 填充 `{{VAR}}` 变量后发给 subagent。

其中 Step 0 现在采用“双模板/按能力裁剪”：

- `tpl-interview-structured-ui.md`：结构化采访 UI 模式
- `tpl-interview-text-fallback.md`：文本回退模式
- `tpl-interview.md`：共享采访核心，不直接作为运行时模板
- `module-structured-interview-ui.md` / `module-text-interview-fallback.md`：模式模块，通过 `--inject-file` 注入运行时模板

P2A/P2B/P3/P3.5/P4 均采用渐进式上下文注入：每个节点有 orchestrator + phase1 + phase2（Step4 为 phase1/2/3），subagent 内部按阶段自主读取。

| 模板 | 阶段 | 说明 |
|------|------|------|
| `tpl-interview.md` | Step 0 核心 | 共享采访问题合同，不直接运行 |
| `tpl-interview-structured-ui.md` | Step 0 采访 | Structured UI 模式 |
| `tpl-interview-text-fallback.md` | Step 0 采访 | Text Fallback 模式 |
| `module-structured-interview-ui.md` | Step 0 模块 | Structured UI 模式协议 |
| `module-text-interview-fallback.md` | Step 0 模块 | Text Fallback 模式协议 |
| `tpl-research-synth-orchestrator.md` | Step 2A 调度 | 轻量 orchestrator |
| `tpl-research-synth-phase1.md` | Step 2A 搜索 | 搜索与搜集 |
| `tpl-research-synth-phase2.md` | Step 2A 整理 | 数据格式化+自审 |
| `tpl-source-synth-orchestrator.md` | Step 2B 调度 | 轻量 orchestrator |
| `tpl-source-synth-phase1.md` | Step 2B 提炼 | 资料读取与提炼 |
| `tpl-source-synth-phase2.md` | Step 2B 自审 | 质量自审+边界校验 |
| `tpl-outline-orchestrator.md` | Step 3 调度 | 轻量 orchestrator |
| `tpl-outline-phase1.md` | Step 3 编写 | 大纲编写 |
| `tpl-outline-phase2.md` | Step 3 自审 | 严格自审+修复 |
| `tpl-style-orchestrator.md` | Step 3.5 调度 | 轻量 orchestrator |
| `tpl-style-phase1.md` | Step 3.5 决策 | 约束提炼+风格输出 |
| `tpl-style-phase2.md` | Step 3.5 自审 | 字段合同自审 |
| `step4/tpl-page-orchestrator.md` | Step 4 调度 | 渐进式 orchestrator（统一执行后端） |
| `step4/tpl-page-planning.md` | Step 4A 规划 | 页面策划 |
| `step4/tpl-page-html.md` | Step 4B HTML | 设计稿生成 |
| `step4/tpl-page-review.md` | Step 4C 审查 | 图审修复 |


## 资源库

`scripts/resource_loader.py` 管理 7 个运行期资源目录：

- **menu 模式**：提取所有 `# 标题` + `> 引用`（多行 blockquote）-> planning 阶段消费，也可先落盘成 `runtime/page-planning-menu-N.md` 快照
- **resolve 模式**：按 planning JSON 字段路由加载对应资源正文 -> html 阶段消费

字段路由表：

| planning 字段 | 资源目录 |
|---------------|---------|
| `layout_hint` | `layouts/` |
| `card_type` | `blocks/` |
| `chart_type` | `charts/` |
| `page_type` | `page-templates/` |
| `resources.*_refs` | 对应目录 |

说明：

- `cover` / `toc` / `section` / `end` 这类非 `content` 页，主消费链是 `page_type -> page-templates/`
- `resources.page_template` 是显式覆盖口，只有需要强制钉住某个模板正文时才额外填写

## Design Runtime

数据到视觉的桥梁文件：

| 文件 | 用途 |
|------|------|
| `data-type-visual-mapping.md` | 数据类型 -> card_type + layout + CSS 实现参考 |
| `data-type-decoration-mapping.md` | 数据类型 -> 装饰技法(T) + 武器(W) + 密度 |
| `design-specs.md` | 画布规范、排版阶梯、卡片规则 |
| `css-weapons.md` | CSS 高级武器库 W1-W12 |
| `director-command-rules.md` | director_command 运行规则 |
| `director-command-examples.md` | 10 种页面类型示例库 |

## Style Runtime

风格目录同时包含两类材料：

- 预置风格参考：`blue-white.md`、`dark-tech.md` 等 8 个风格文件
- runtime 风格合同：`runtime-style-rules.md` 与 `runtime-style-palette-index.md`

其中：

- Step 3.5 默认直接注入 runtime 风格合同与预置风格入口
- 具体预置风格文件只在 style subagent 需要细看某个候选基底时按需读取
- `runtime-*` 文件不是页面 planning / html 阶段的 menu 资源

## 单一真源与自检

当前 skill 维持 markdown-first 架构，但以下事实只允许一个地方说了算：

- **Step 4 schema / 枚举 / planning 合法值**：`scripts/planning_validator.py`
- **prompt 变量需求**：各 `references/prompts/tpl-*.md`
- **资源存在性与归一化**：`references/` 真实文件 + `scripts/resource_loader.py`
- **主链命令编排**：`references/cli-cheatsheet.md`
- **多阶段完成信号**：各 orchestrator 模板

维护时先改真源，再改说明层；改完运行：

```bash
python3 scripts/check_skill.py
python3 scripts/smoke_skill.py
```

该检查会至少覆盖：

- `cli-cheatsheet.md` 中的 `prompt_harness.py` 调用是否把模板变量传全
- 非末阶段 phase1 模板是否错误发送最终 `FINALIZE`
- Step 4 文档是否混入已废弃的旧别名
- Step 4 planning 示例 JSON 是否真能通过 `planning_validator.py`
- Step 3 的 `density_bias` 大纲合同、Step 4 的 `density_label / density_contract` 示例、`visual_qa.py` 双层断言、`resource_loader.py`、`prompt_harness.py` 主链是否还能最小串通（`smoke_skill.py`）

## 维护规则

- 新增资源文件放到对应目录，`resource_loader.py` 自动发现
- 每个资源文件必须有 `# 标题` + `> 多行引用`（数据类型、适用场景、约束）
- 不要在根目录放文件，不要创建新的子目录
- `runtime-*` 前缀的文件被 resource_loader 的 menu / resolve 流程跳过（仅供主链或特定 runtime 阶段直接读取）
