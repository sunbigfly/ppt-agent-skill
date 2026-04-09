---
name: ppt-agent
description: 专业 PPT 演示文稿全流程 AI 生成助手。模拟顶级 PPT 设计公司的完整工作流（需求调研到资料搜集到大纲策划到策划稿到设计稿），输出高质量 HTML 格式演示文稿。当用户提到制作 PPT、做演示文稿、做 slides、做幻灯片、做汇报材料、做培训课件、做路演 deck、做产品介绍页面时触发此技能。即使用户只说"帮我做个关于 X 的介绍"或"我要给老板汇报 Y"，只要暗示需要结构化的多页演示内容，都应该触发。也适用于用户说"帮我把这篇文档做成 PPT"、"把这个主题做成演示"等需要将内容转化为演示格式的场景。英文场景同样适用："make a presentation about..."、"create slides for..."、"build a pitch deck"、"I need a keynote for..."。隐式意图也应触发："帮我把这个数据可视化一下给老板看"、"我需要一份能拿去路演的东西"、"把这个报告做得好看点能展示"、"beautify my existing PPT"、"redesign these slides"。改善或美化现有 PPT 也属于此技能范畴。
---

# PPT Agent v4.1 — 主控制台合同

## 1. 主 Agent 角色

**只做**：维护计划、调用 harness、管理 subagent 生命周期、校验 Gate、与用户交互。

**不做**：代写任何正式产物；手写 subagent prompt；内联执行任何内容生产；用口头判断替代 validator。

**内容生产全量外包红线**：P2A/P2B/P3/P3.5/P4 的所有正式产物（search.txt、source-brief.txt、outline.txt、style.json、planningN.json、slide-N.html 等）**必须且只能**由对应的 subagent 生成。主 agent 自己写出这些产物内容 = 合同违规。主 agent 唯一允许的"写"行为是通过 harness 生成 prompt 文件和通过 validator 校验产物。

## 2. 全局规则

### 2.1 步骤控制

- **CLI 固定步骤锁（强制）**：必须严格按 Canonical Plan 的主链 `P0 → P1 → (P2A|P2B) → P3 → P3.5 → P4 → P5` 执行；禁止增删改名。
- 分支二选一：进入 P2A 后绝对不可再跑 P2B，反之亦然。
- **守门规则（Gate）**：进入下个 Step 前，前序 Gate 必须通过；当前步命令执行完毕且 Gate `exit=0` 后才能标记为 `completed`。
- 失败时只允许两种动作：`RETRY_CURRENT_STEP` 或 回退 `ROLLBACK→StepID`。**严禁"跳到后续步骤试试看"**。
- `WAIT_USER` / `WAIT_AGENT` 是硬等待点；未收到输入/FINALIZE 前，**禁止执行后续步骤**。
- **人工审计断点**：是否开启、介入哪些节点、可看哪些材料，必须在 Step 0 采访时写入 `requirements-interview.txt`。断点只能挂在既有主链 Step 内，且只允许主 agent 控制；subagent 不得自行向用户发问。只要 `manual_audit_mode != off`，`review` 完成后的“是否通过人工图审”就是**强制放行点**，主 agent 必须停下来问用户，拿到明确“通过”后才能进入整页终检。

### 2.2 Subagent 强制调度（核心约束）

**通用生命周期**：`create(--model SUBAGENT_MODEL) → RUN(prompt路径) → STATUS… → FINALIZE → close`；完成即关，不复用。Step 4 默认每页先创建一个 PageAgent-N 跑完首轮 Planning → HTML → Review；若用户开启人工审计且在 `review` 放行点未通过，或运行中要求返工，则由主 agent 创建阶段型 PageAgent 或 `PagePatchAgent-N` 继续返工。创建时**必须**显式传 `--model SUBAGENT_MODEL`，禁止省略。`SUBAGENT_MODEL` 由用户在 Step 0 采访时指定（详见 3.1.0 及 6.2）。

**上下文隔离（强制）**：无论 CLI 环境默认是否让 subagent 继承主 agent 上下文，本 skill 要求所有 subagent 必须以**隔离模式**运行——subagent 唯一可见的上下文是主 agent 通过 prompt 文件显式传递的内容。如果 CLI 支持隔离参数（如 `--no-context`、沙箱模式等），必须在《Subagent 操作手册》中记录并在调用模板中包含。主 agent 的对话历史、SKILL.md 内容、环境变量等**不应该**泄露给 subagent。

**Subagent 强制调度表（每行 = 一个必须创建的 subagent）**：

| Step | Subagent 类型 | 职责 | 产物 | 主 agent 行为边界 |
|------|--------------|------|------|------------------|
| P2A | ResearchSynth | 联网检索 + 素材整理 | search.txt, search-brief.txt | 仅 harness 生成 prompt → 创建 subagent → 回收校验 |
| P2B | SourceSynth | 用户资料降维整合 | source-brief.txt | 同上 |
| P3 | Outline | 大纲构建（含内部自审闭环） | outline.txt | 同上，禁止介入 subagent 内部自审 |
| P3.5 | Style | 全局风格锁定 | style.json | 同上 |
| P4 | PageAgent-N（每页一个） | 页面规划 + HTML + 审查 | planningN.json, slide-N.html, slide-N.png | 同上，orchestrator 渐进式编排三阶段 |

**红线**：
- 上表中每个 Step 的产物**只允许对应 subagent 生成**，主 agent 内联生产任何产物 = 合同违规
- 即使 subagent 失败，主 agent 也只能重建 subagent 重跑，不能自己"补写"产物
- 图片模式 `generate` 且用户需要文生图时，额外创建 `ImageGen` 子代理；PageAgent 不承担文生图
- 若用户在人工审计断点提出改单，尤其是在 `review` 后强制放行点给出“不通过”，主 agent 也**必须**通过阶段型 PageAgent 或 `PagePatchAgent-N` 返工；默认从 `review` 重开，让 subagent 继续图审 + HTML 修复；严禁主 agent 直接手改正式产物

**自适应调用协议（每个业务节点强制执行）**：

主 agent 到达上表任意 Step 时，必须按以下流程显式组装 subagent 调用命令：
1. **回查** Section 3.1.1 输出的《Subagent 操作手册》，取出其中的**调用模板**（模型槽位使用 `SUBAGENT_MODEL`）
2. **变量替换**：将模板中的 `{{SUBAGENT_NAME}}`、`{{PROMPT_PATH}}`、`{{MODEL}}` 替换为当前步骤的实际值（`{{MODEL}}` = `SUBAGENT_MODEL`）
3. **显式输出**：将组装后的完整命令输出到对话中（不是脑内执行，是显式写出来）
4. **执行**：按输出的命令执行 subagent 创建、RUN、轮询、回收

禁止“依据操作手册创建”这种含糊引用；必须显式展示组装结果。

### 2.3 Prompt 生成

- 所有 subagent prompt 必须通过 `prompt_harness.py` 从模板生成；禁止手写
- 所有 `{{VAR}}` 必须填充，残留即 ERROR；输出固定落 `OUTPUT_DIR/runtime/`
- 模板/playbook 仅通过 `--inject-file` 注入；主 agent 不手动预读正文
- **Step 0 默认强制模板化**：主 agent 必须先通过 `prompt_harness.py` 生成 `OUTPUT_DIR/runtime/prompt-interview.md`，再依据渲染结果向用户发问；采访运行时模板必须按能力在 `tpl-interview-structured-ui.md` 与 `tpl-interview-text-fallback.md` 之间二选一，不得退化成随手写的一小段简陋问题。
- **Step 0 优先结构化采访 UI**：只要当前 CLI 提供任何等价于 `AskUserQuestion` / `request_user_input` 的原生提问能力，主 agent 就必须优先使用；能力判断看是否支持 `question/header/id/options` 等结构化提问对象，而不是看固定工具名。
- **Step 0 文本回退也必须结构化**：若当前 CLI 不支持结构化采访 UI，主 agent 必须回退为分组明确的 Markdown 采访单；不得退化成一行填空或散乱问题串。
- **Step 0 唯一例外**：仅当 `prompt_harness.py` 在 Step 0 发生真实脚本接口故障，并已判定 `BLOCKED_SCRIPT_INTERFACE` 时，才允许主 agent 直接发问；但覆盖维度不得低于 `tpl-interview.md` 的最终要求。

### 2.4 通信协议

| 指令 | 方向 | 内容 |
|------|------|------|
| **RUN** | 主→子 | prompt 文件路径（一行，不发正文）|
| **STATUS** | 子→主 | 进度、阻塞项、下一动作 |
| **FINALIZE** | 子→主 | 完成信号 + 产物路径列表 |

仅里程碑通信；任何修复直接改文件并回传路径。

**多阶段 orchestrator 补充协议**：对于 `phase1 → phase2 [→ phase3]` 的渐进式子代理，**非末阶段只允许输出** `--- STAGE n COMPLETE: {artifact_path} ---` 作为阶段完成标记；**只有最后阶段才允许发送 FINALIZE**。

### 2.5 校验双保险

subagent FINALIZE 前自审；主 agent 回收后再跑同一 validator 复检。自审通过不等于主链放行。

### 2.6 执行纪律

- **执行优先策略**：到达某一步后，直接执行该步的 harness/CLI 命令，不要擅自做无关探索。
- **采访前置锁定**：完成 3.1 环境感知、`update_plan` 与 `cli-cheatsheet` 读取后，第一条**面向用户的业务交互**必须是 Step 0 的采访问题；允许把 `## 模型感知结果` / `## Subagent 操作手册` / `## 采访 UI 能力` 压缩为同一条消息里的前置状态块，但**不得先做调研、资料探索或报告读取**。
- **阅读隔离边界**：未到对应步骤时禁止读对应阶段文件；主 agent **可读内容仅限**：`OUTPUT_DIR/**`、用户输入资料、以及 `cli-cheatsheet.md`。
- **把脚本当做黑盒工具**：`scripts/*.py` 是执行对象，不是阅读对象！**仅允许 `python3 ...` 执行**；严禁对脚本跑 `--help` 摸索参数，严禁 `cat` 脚本源码！所需的参数全都在 `cli-cheatsheet.md` 里面。
- 如果命令失败：首先对照 cheatsheet 核对参数形式；解决不了则立刻标记 `BLOCKED_SCRIPT_INTERFACE` 并呼叫用户裁决。
- **汇报纪律**：只汇报"目标动作、执行结果、Gate反馈"；严禁长篇大论的 "Explored files..." 预读清单。

### 2.7 资源双层消费

资源文件结构：`# 标题` + `> 一句话定位（引用层）` + 正文层。消费规则：

- planning 阶段：`resource_loader.py menu` 加载标题+引用层组成菜单
- planning 阶段主链需先把 menu 结果落一份 `runtime/page-planning-menu-N.md` 备份，再让 PageAgent 读取这份快照
- html 阶段：`resource_loader.py resolve` 按 planning JSON 字段动态加载正文层
- 字段路由：`layout_hint→layouts/`、`page_type→page-templates/`、`card_type→blocks/`、`chart_type→charts/`

命令见 cheatsheet 资源路由节。

## 3. 环境、路径与产物合同

### 3.1 环境感知（至关重要，Step 0 前强制完成）

进入任何业务步骤前，主 agent 必须按照以下顺序执行环境感知，并将结果**显式分类记录到对话或计划日志**中。这决定了整个任务的工具下限。若当前界面会直接暴露给用户，允许把这些结果压缩成采访消息中的前置状态块；禁止在 Step 0 前展开长篇说明。

**前置操作：**
1. 先调用 `update_plan` 创建 canonical plan。
2. 必须读取 `references/cli-cheatsheet.md` 建立对所有 CLI 接口的精确记忆。

#### 3.1.0 模型与思考深度感知（Model & Thinking Effort Perception）
为了绝对保证内容质量不滑坡，主 agent 必须在开局时确认自己是谁，并在采访阶段确认 subagent 使用的模型及思考等级：
1. **强行识别当前主 agent 正在使用的大模型版本**（例如 Claude-3.5、Gemini-1.5 等，如果无法确认直接问用户）。
2. 将其在心中显性固化为 `MAIN_MODEL` 全局变量，并在对话中输出 `## 模型感知结果`。同时也需探测当前环境 API/工具是否支持给模型传递"思考深度/推理努力(reasoning effort)"这一级选项。
3. **`SUBAGENT_MODEL` 与 `SUBAGENT_THINKING_EFFORT` 绑定**：Step 0 采访阶段不仅会向用户确认 subagent 使用的模型，还会询问需要的**思考深度等级**（详见 6.2）。用户回答后，将其显性固化为 `SUBAGENT_MODEL` 和 `SUBAGENT_THINKING_EFFORT` 全局变量，并在 `## 模型感知结果` 中同步输出。
4. **全局防降格红线**：一旦确认这两个变量，在后续流程中创建任何 Subagent 时，必须强制将其带入构建参数中（绝对禁止走默认回退配置）。

#### 3.1.1 Subagent 操作手册生成
环境中有多种执行工具，主 agent 必须为自己梳理规矩：
1. 自检环境中用于创建管理 agent/subagent 的技能或 API。
2. 检查这些工具是否支持模型重载参数（对应 3.1.0）。
3. 整理出支持情况并输出到对话，标题固定为 `## Subagent 操作手册`，必须包含以下内容：
   - **工具名称**：当前环境可用的 subagent 创建工具
   - **调用模板（必须含变量槽）**：一个可参数化的命令模板，包含 `{{SUBAGENT_NAME}}`、`{{PROMPT_PATH}}`、`{{MODEL}}` 以及支持深度思考情况下的 `{{THINKING_EFFORT}}` 等四个槽位。
   - **示例调用**：用具体值填充槽位的实例

   调用模板示例（主 agent 必须根据实际环境生成类似格式，`{{MODEL}}` = `SUBAGENT_MODEL`，`{{THINKING_EFFORT}}` = `SUBAGENT_THINKING_EFFORT`）：
   ```
   # 模板（槽位用 {{}} 标记，MODEL 取自 SUBAGENT_MODEL，THINKING_EFFORT 取自 SUBAGENT_THINKING_EFFORT）
   <tool> --model {{MODEL}} --reasoning-effort {{THINKING_EFFORT}} --message "Read {{PROMPT_PATH}} and execute all instructions" --name {{SUBAGENT_NAME}}
   ```

4. 此后每个业务节点调用 subagent 时，必须回查此模板、替换变量、**显式输出组装后的完整命令到对话中**，然后执行。禁止“依据操作手册”这种含糊引用。

#### 3.1.2 采访 UI 能力探测

由于 Step 0 直接决定用户交互体验：
1. 主 agent 必须自检当前 CLI 是否提供原生结构化提问 UI。
2. 判断标准：是否存在可提交 `question/header/id/options` 一类结构化字段，并让用户直接点选/填写的能力；名称不限，可表现为 `AskUserQuestion`、`request_user_input`、`ask_user_question`、`ui.form` 等。
3. 将结论以 `## 采访 UI 能力` 输出到对话中，至少包含：
   - 是否支持结构化采访 UI
   - 工具名称或能力形态
   - 是否支持单选 / 多选 / 自由补充
   - Step 0 实际执行策略：`structured-ui` / `text-fallback`
4. Step 0 发问前，必须先回查这一结论；支持则使用 `tpl-interview-structured-ui.md`，不支持则使用 `tpl-interview-text-fallback.md`。

#### 3.1.3 Search 工具清单探测
由于 Research 分支极度依赖网络检索能力：
1. 主 agent 自检所有带有 web search 或直接读取 URL 功能的系统工具及自定义 skill。
2. 梳理支持项，输出名为 `## Search 工具清单` 的表格到对话中。
3. **此步生成的清单，将在 Step 2A 通过 `TOOLS_AVAILABLE` 变量直接喂给检索子代理，务必清晰详实。**

#### 3.1.4 兜底能力检查
如果缺失基础能力，必须主动停止并报错：
- 文件读写、Python、规划：**必须具备**，无则直接停止流程。
- 信息检索：尽量具备，若无可主动建议用户仅走 Step 2B 修改本地资料。
- 图像生成：若无实际工具支持，强制后续图片策略降级为 `manual_slot` 或 `decorate`。

### 3.2 路径变量

| 变量 | 值 |
|------|----|
| `SKILL_DIR` | 当前 skill 根目录（例如：`../skills/ppt-agent-workflow-san`，**必须是相对路径**） |
| `ROOT_OUTPUT_DIR` | `ppt-output/`（必须相对 CWD，禁止跳出） |
| `RUN_ID` | `YYYYMMDD-HHMMSS-topic`（带时间戳用于区分同目录下不同任务的产出） |
| `OUTPUT_DIR` | `ROOT_OUTPUT_DIR/runs/{RUN_ID}` |

**RUN_ID 唯一性约束**：同一个 PPT 任务全程只允许一个 RUN_ID，Step 0 创建后锁定复用，重试/回退/断点恢复均复用同一个，禁止为同一任务重复创建。不同的 PPT 任务（不同主题）各自独立 RUN_ID。恢复旧任务时绑定旧 RUN_ID。

> **⚠️ 跨环境可移植性红线（防止运行时路径污染）**：
> 在组装并向 `prompt_harness.py` 传入用于子代理指引的变量时，主 Agent **绝对禁止**将其展开成宿主的死硬绝对路径（如 `/home/xxxxxxxx/...`），也尽量避免结构极度脆弱的外跳路径（如 `../../../.gemini/...`）。
> 
> **最聪敏的终极解决方案**：
> 1. 对于引擎代码路径（如 `--var SKILL_DIR=` 或 `--var REFS_DIR=`），主 agent 请直接传递**带有环境变量字面量**的字符串本身（如 `--var SKILL_DIR='$SKILL_DIR'`、`--var REFS_DIR='$SKILL_DIR/references'`）。
> 2. 这样最终生成的 `OUTPUT_DIR/runtime/prompt-*.md` 模板内容里，就会直接保留 `python3 $SKILL_DIR/scripts/...` 这种占位符。子代模型也会乖乖地用这样的环境变量向终端请求执行，任何终端只要配置了 `$SKILL_DIR` 都可以瞬间通跑我们的产物！
> 3. 对于业务流水线位置（`OUTPUT_DIR` 相关），必须退化成基于 CWD 的干净相对路径。
### 3.3 正式产物链

```text
interview-qa.txt → requirements-interview.txt
  → search.txt + search-brief.txt（research）| source-brief.txt（非 research）
  → outline.txt → style.json
  → planning/planningN.json → slides/slide-N.html → png/slide-N.png
  → preview.html → presentation-{png,svg}.pptx → delivery-manifest.json
```

运行时 prompt 落 `OUTPUT_DIR/runtime/prompt-*.md`。

## 4. Canonical Plan

> !强制使用CLI 原装plan list工具管理所有task

```text
P0.01  采访问题组装
P0.02  [WAIT_USER] 获取回答
P0.03  写入 interview-qa.txt
P0.04  归一化 → requirements-interview.txt

P1.01  输入识别
P1.02  [WAIT_USER] 分支选择（research / 非research）

P2A.01 harness → phase1 + phase2 + orchestrator prompt
P2A.02 创建 ResearchSynth subagent（发 orchestrator，subagent 内部自主渐进：搜索 → 格式化+自审）
P2A.03 [WAIT_AGENT] FINALIZE
P2A.04 回收校验（search.txt + search-brief.txt）
P2A.05 [可选] 回退 P2A.01 扩搜重跑
P2A.06 关闭

P2B.01 [如 pptx][WAIT_USER] 模式确认
P2B.02 资料初读与方向提炼（梳理 3-5 个可能的陈述切入方向）
P2B.03 [WAIT_USER] 强制展示方向并获取用户选择
P2B.04 将用户选定方向写入 requirements-interview.txt
P2B.05 harness → phase1 + phase2 + orchestrator prompt
P2B.06 创建 SourceSynth subagent（发 orchestrator，subagent 内部自主渐进：提炼 → 自审）
P2B.07 [WAIT_AGENT] FINALIZE
P2B.08 回收校验（source-brief.txt）
P2B.09 关闭

P3.01  harness → phase1 + phase2 + orchestrator prompt
P3.02  创建 Outline subagent（发 orchestrator，subagent 内部自主渐进：编写 → 自审+修复）
P3.03  [WAIT_AGENT] FINALIZE
P3.04  回收校验 outline.txt
P3.05  关闭

P3.5.01 harness → phase1 + phase2 + orchestrator prompt
P3.5.02 创建 Style subagent（发 orchestrator，subagent 内部自主渐进：决策 → 自审）
P3.5.03 [WAIT_AGENT] FINALIZE
P3.5.04 回收校验 style.json
P3.5.05 关闭

P4.NN.01 生成 Step 4 planning 菜单快照 + runtime prompt
P4.NN.02 创建当前轮 subagent（首轮：PageAgent-NN；断点返工：阶段型 PageAgent 或 PagePatchAgent-NN）
P4.NN.03 [WAIT_AGENT] 回收当前轮 FINALIZE（拿到最新 planning/html/png）
P4.NN.04 [如 manual_audit_mode != off][WAIT_USER] 展示最新 slide-N.png，询问是否通过人工图审
P4.NN.05 [如未通过] 创建 `PagePatchAgent-NN`（默认 `START_STAGE=review, END_STAGE=review`）执行图审 + HTML 修复，然后回到 `P4.NN.03`
P4.NN.06 整页终检（产物校验 + visual_qa + 主 agent 看图）
P4.NN.07 关闭当前页 subagent
（所有页并行推进）

P5.01  生成 preview.html
P5.02  PNG 导出 → presentation-png.pptx
P5.03  SVG 导出 → presentation-svg.pptx
P5.04  写入 delivery-manifest.json
```

**Plan 更新规则**：仅状态变化时更新；并行页逐页追踪不合并；create/wait/close 拆开；generate/validate 拆开；回退显式标记 `ROLLBACK→StepID`。

## 5. 调度骨架与真源

### 5.1 统一 Subagent 调度骨架（P2A/P2B/P3/P3.5/P4 共用）

1. 查 cheatsheet 对应步骤 → harness 生成阶段 prompt 文件（phase1 + phase2 [+ phase3]）
2. harness 生成 orchestrator prompt（轻量调度，只含阶段路径 + 渐进式执行协议）
3. 按《Subagent 操作手册》创建 subagent（必须传 `--model SUBAGENT_MODEL`）
4. 发送 `RUN`（orchestrator prompt 路径）→ subagent 内部自主渐进式读取各阶段 → 收到 FINALIZE
5. 主 agent 执行 gate 复检；若是 Step 4 且 `manual_audit_mode != off`，则 FINALIZE 后必须先经过 `review` 后的 `[WAIT_USER]` 放行点，再进入整页终检 → 不再复用时立即 close

### 5.2 真源索引

| 类别 | 路径 | 消费方式 |
|------|------|---------|
| Prompt 模板 | `references/prompts/tpl-*.md` | 传路径给 harness，不手动预读 |
| 执行细则 | `references/playbooks/*-playbook.md` | `--inject-file` 注入 |
| 风格真源 | `references/styles/runtime-style-*.md` | Step 3.5 注入 |
| 大纲/采访/交付合同 | `scripts/contract_validator.py` | P0 / P3 / P5 Gate |
| Step 4 schema 真源 | `scripts/planning_validator.py` | P4 planning Gate |
| Step 4 图审与结构校验 | `scripts/visual_qa.py` | P4 PNG + planning + HTML 双层 Gate |
| CLI 命令 | `references/cli-cheatsheet.md` | Step 0 前读取，后续直接引用 |

`CURRENT_BRIEF_PATH`：research → `search-brief.txt`；非 research → `source-brief.txt`（Step 3/4 共用）。

### 5.3 单一真源与自动检查

- **workflow / schema 版本真源**：`scripts/workflow_versions.py`（当前 `WORKFLOW_VERSION = 2026.04.09-v4.1`）
- **Step 4 schema 真源**：`scripts/planning_validator.py`
- **outline 密度合同真源**：`scripts/contract_validator.py`
- **Step 4 结构/像素双层校验真源**：`scripts/visual_qa.py`
- **prompt 变量真源**：各 `references/prompts/tpl-*.md` 模板中的 `{{VAR}}`
- **资源 ID 真源**：`references/layouts/`、`references/blocks/`、`references/charts/`、`references/principles/` 的真实文件 stem，与 `scripts/resource_loader.py` 的归一化规则
- **多阶段完成信号真源**：各 orchestrator 模板中的阶段协议
- **自动检查入口**：修改 prompt/playbook/cheatsheet/Step 4 schema 示例后，运行 `python3 SKILL_DIR/scripts/check_skill.py`

## 6. 主流程状态机

### 6.1 Step 全景表

| Step | 核心动作 | 关键产物 | Gate | 失败回退 |
|------|---------|---------|------|---------|
| P0 | 采访并归一化需求 | interview-qa.txt / requirements-interview.txt | `contract_validator interview` + `requirements-interview` | 补问，不进 P1 |
| P1 | 识别输入确定分支 | 分支写入 requirements-interview.txt | 逻辑判断 | WAIT_USER |
| P2A | 检索并压缩资料 | search.txt / search-brief.txt | `contract_validator search` + `search-brief` | 回退 `P2A.01` 重建 ResearchSynth（扩大搜索预算/维度） |
| P2B | 压缩用户现有资料 | source-brief.txt | `contract_validator source-brief` | 回 P2B 重写 |
| P3 | 生成大纲（内部自审） | outline.txt | `contract_validator outline`（含 `density_bias / density_curve / 单页密度窗口`） | 回退 `P3.01` 重建 Outline subagent，最多 2 轮；仍失败则 `BLOCKED_OUTLINE` 呼叫用户裁决 |
| P3.5 | 固定全局风格 | style.json | `contract_validator style` | 回 P3.5 |
| P4 | 并行生产各页 | planningN.json / slide-N.html / slide-N.png | `planning_validator` + 三件套存在性 + `visual_qa`（PNG + planning + HTML）+ 主 agent 看图 + （若开启）用户人工图审通过 | 只回退该页；人工图审未通过时默认从 `review` 重开；同类 P0/P1 连续 2 轮不收敛则强制回退 `planning` |
| P5 | 导出交付 | preview.html / 双 pptx / delivery-manifest.json | `contract_validator delivery-manifest` | 只回退导出 |

> 所有命令完整参数见 `cli-cheatsheet.md`。

### 6.2 Step 0 采访（核心起点，不可跳过）

即使第一句话用户提供了极多信息，**严禁跳过采访阶段**。
- **高效推进**：采访直接收集所需字段信息，不生成解释性分析与背景描述。
- **默认执行方式**：优先按环境能力生成使用结构化采访 UI（`tpl-interview-structured-ui.md`），若不支持则用格式清晰且附带选项的文本问答（`tpl-interview-text-fallback.md`）。
- **结构化输出约束**：通过提示向用户提供明确的备选项。最终收集的字段组合必须高度结构化、数据详实，能直接输出至 `requirements-interview.txt` 并 100% 被下游验证器（Gate）与子系统（Subagent）解析消费，无需推测与加工。
- **必须覆盖但允许精简（如果已知）的维度**：场景、受众、核心传达目标、期望页数与密度、风格倾向、品牌规范、配图策略、资料使用范围，以及是否参与中间人工审计。
- **密度归一化约定（Step 0 就要定死）**：用户填写的 `page_density` 只表示整套 deck 的整体倾向，不等于每页固定密度。内部统一映射为 `density_bias`：
  - `少而精 -> relaxed`
  - `适中 -> balanced`
  - `容量极大 -> ultra_dense`
- 后续单页差异由 `outline` 产出的 `density_curve` 决定，不交给 `html` 临场发挥。
- **subagent 模型与思考深度（必问）**：直截了当让用户选「后续子系统使用什么模型，以及需要何种等级的思考深度？」（如低/中/高，或者普通/深度思考，视当前模型生态而定）。选出后分别固化在 `SUBAGENT_MODEL` 和 `SUBAGENT_THINKING_EFFORT` 全局变量。如果用户不关心，可以默认 `SUBAGENT_MODEL = MAIN_MODEL` 并使用中等思考等级。
- **人工审计参与方式（必问）**：至少固化 `manual_audit_mode`、`manual_audit_scope`、`manual_audit_assets` 这 3 个字段；具体选项与提问形式放在采访模板里维护，不在 `SKILL.md` 展开。
- 只有所有重要选项收集齐并固化入 `requirements-interview.txt`（必须包含模型、思考深度和人工审计参数），才能进入 Step 1。

### 6.3 Step 1 分支确立

这是流程分水岭。
1. 识别并归类用户输入（大段文本、单文件、多文件、现成 pptx）。
2. **强制向用户确认分支**：需要「联网重新检索扩写（Research 分支）」，还是「限定只用当前本地资料（非 Research 分支）」。
3. 得到回答后，将分支写入 `requirements-interview.txt`。

### 6.4 Step 2A Search-Lite（Research 分支专有）

此阶段极易发生两个极端：内容单薄 或 无限制搜索烧 Token。

**搜索深度预估（主 agent 在生成 prompt 前必须完成）**：
- **丰富度优先**：搜索的首要目标是为每页提供足够丰富的素材（数据、案例、引用），宁可多搜一轮也不要内容单薄。
- 根据主题复杂度和目标页数，预估搜索轮次上限（`MAX_SEARCH_ROUNDS`）并写入 prompt 变量：
  - 简单/熟知主题（公司介绍、产品宣讲等）：**2 轮**
  - 中等复杂度（行业趋势、技术方案等）：**3 轮**
  - 高复杂度（深度研究报告、多维竞品分析等）：**4 轮**
- 每轮搜索后 subagent 须自评覆盖率：若数据类型已覆盖目标页数需求且素材充裕，可提前终止；若某维度明显空缺，应继续搜索直到达到上限。
- `MAX_SEARCH_ROUNDS` 是硬上限而非目标——鼓励在上限内尽可能搜全，但到达上限后必须收敛出 brief，禁止无限追加。

**强制检查项**：产出的 `search-brief.txt` 必须包含专为 PPTX 设计的独立结构化数据包区块。必须至少含 3 种不同数据类型（Metrics指标、Comparisons对标、Timelines时间线等）。
- 若搜索质量偏低且未达 `MAX_SEARCH_ROUNDS`，主 agent 应**回退到 `P2A.01` 重建一套新的 ResearchSynth prompt 与 subagent**，扩大搜索预算/维度后整步重跑；不要在已 FINALIZE 的 session 上继续补搜。
- 若已达上限仍不满足，标记 `SEARCH_QUALITY_LOW` 并向用户说明缺口，由用户决定是否补充资料或降低预期。

### 6.5 Step 2B 本地资料压缩（非 Research 分支）

用户丢来的一堆资料必须先处理好再跑大纲。**此步同样走 subagent 模式**（SourceSynth subagent），但为了避免黑盒决定方向且保证方向贴合业务，必须在此阶段引入用户决策。禁止主 agent 内联执行正式内容生产，但允许浅度摸底。

1. **[特例] pptx 模式确认**：若用户直接传了 `.pptx`，主 agent 须**最先**强制询问期望的处理模式（仅美化排版 / 彻底重构大纲 / 美化排版并重构内容）。
2. **[防黑盒] 资料初读与方向提炼**：主 agent （或调用其他轻量解析工具）必须对用户现有的资料做一次快速摸底通读，提炼出 3-5 个可能的**PPT 核心陈述方向/切入视角**（例如：以技术机制为侧重点 vs 以商业价值为侧重点）。
3. **强制确认方向**：通过 `[WAIT_USER]` 强制向用户提问："基于您提供的资料，我梳理了以下几个讲述方向，您倾向哪种或有其他补充？"。收到用户明确答复后，将此业务方向追加写入 `requirements-interview.txt` 中。
4. 主 agent 通过 harness 生成 SourceSynth prompt（命令见 cheatsheet Step 2B）。
5. 按《Subagent 操作手册》创建 SourceSynth subagent（必须传 `--model SUBAGENT_MODEL`）。
6. SourceSynth 负责：**多文件降维**（doc/excel/pdf/代码 → 纯文本）、**前置理解**（顺着文件 `requirements-interview.txt` 里的强制方向提取主题）、整合输出 `source-brief.txt`。
7. 主 agent 回收 FINALIZE 后执行 Gate 校验。

### 6.6 Step 3 大纲构建（内部闭环）

**核心纪律**：主 agent 不要自作聪明显式开启后续的审查验证轮回。Outline subagent 设计为自带闭环属性，它会在内部按照【打草稿 → 严格自查缺陷 → 覆盖修复】的死循环直到完美状态，只有这样它才会交出带有 FINALIZE 的最终 `outline.txt`。

这一步不只是在排页序，也要先把整套密度节奏定下来：
- `outline` 必须显式产出 deck 级 `density_bias` 和整套 `density_curve`
- 每页必须写完整的 `密度下限 / 密度目标 / 密度上限 / 节奏动作 / 信息姿态 / 锚点类型`
- 共同硬规则：`cover / section / end` 不允许 `dashboard`；禁止连续 3 页 `high / dashboard`；`dashboard` 前后必须至少有 1 页非 `dashboard` 过渡
- `contract_validator outline` 会直接检查这些字段，不允许把“页差”留到 Step 4 再临时决定

### 6.7 Step 3.5 风格锁定（全局卡口）

全盘风格定调。只有在明确了需求文本跑出的大纲后才定风格。风格判断不仅看需求，更依赖 `runtime-style-rules.md`。输出：一份精准的、没有含糊描述、能被页面规划和 HTML 代码直接执行的 `style.json`。

### 6.8 Step 4 单页并行生产（orchestrator 渐进式披露）

为防止大模型在一次 prompt 中同时兼顾排版、图文推演与 HTML 编码导致「注意力塌陷」，本阶段每个单页的任务被拆散成三级 prompt（4A Planning -> 4B HTML -> 4C Review）。

这里的密度合同是冻结点，不是建议项：
- `planning` 必须把 outline 给出的密度窗口冻结成 `density_label`、`density_reason`、`density_contract`
- `density_contract` 至少要包含 `deck_bias`、`page_lower_bound`、`page_upper_bound`、`max_cards`、`max_charts`、`min_body_font_px`、`max_lines_per_card`、`image_policy`、`decoration_budget`、`overflow_strategy`
- `content_budget` 是卡片级硬预算，缺失就算失败；它必须继续服从页级 `density_contract`
- 从这一步开始，`html` 只负责执行，不允许自己抬高或降低本页密度

#### 执行模式

Step 4 只保留两种模式：

1. **自动直通**：主 agent 生成标准 orchestrator prompt，PageAgent 一次跑完 Planning → HTML → Review。
2. **人工审计**：若 `manual_audit_mode != off`，主 agent 可以在 `planning`、`html` 节点挂断点；而在 `review` 节点，用户放行是**强制任务节点**，不是可有可无的旁路。

#### review 后强制放行点

- 只要 `manual_audit_mode != off`，每次 PageAgent / PagePatchAgent 完成一轮 `review`、写出最新 `slide-N.png` 后，主 agent 都必须立刻 `[WAIT_USER]`。
- 此时提问目标固定为：**是否通过人工图审**。只有拿到用户明确“通过”，该页才允许进入整页终检。
- 若用户回答“不通过 / 继续改 / 再审一轮”，主 agent 必须默认创建 `PagePatchAgent-N`，以 `START_STAGE=review`、`END_STAGE=review` 重开，让 subagent 在保留现有 planning 与 HTML 上继续图审 + HTML 修复。
- 只有当用户明确要求重做结构或内容布局时，返工起点才允许从 `html` 或 `planning` 重开。

#### 返工原则

- 用户在断点提出改单，或在 `review` 后强制放行点明确“不通过”时，主 agent **只能**通过阶段型 PageAgent 或 `PagePatchAgent-N` 返工，不能自己改正式产物。
- 返工起点只允许是 `planning` / `html` / `review` 三选一；其中 `review` 后人工图审未通过时，默认从 `review` 重开；只有用户明确要求重做结构时，才回退到 `html` 或 `planning`。
- 断点材料、外挂 orchestrator 组装方式、以及 `PagePatchAgent-N` 的调用模板，都放在 `cli-cheatsheet.md` 的 Step 4 中维护。

#### 共通规则

- 各页可以且应当**并行推进**。
- `HTML` 必须完全服从 `planning`：`low / mid_low` 可高自由度，`medium` 中自由度，`high / dashboard` 低自由度。高密页统一优先稳态 `grid / flex`、短语化文案、表格/矩阵/微图表；禁 `hero image`、禁重装饰、禁多个主锚点并列、禁靠复杂绝对定位硬塞内容。
- `review` 必须先核对 `density_contract`，再看 PNG 视觉质量。
- 如果同一个 `P0 / P1` 类别在连续 2 轮新截图里仍不收敛，说明问题已经回到预算或骨架层，必须停止继续修 HTML，强制回退 `planning`，重写 `density_label / density_contract / layout_hint / cards 分配` 中至少一项。
- **阶段放行条件**：三件套（planningN.json + slide-N.html + slide-N.png）必须齐全，`planning_validator` 必须放行；整页 FINALIZE 回收后，主 agent 还必须补跑 `visual_qa --html` 并亲自看图；若开启人工审计，还必须拿到用户在 `review` 后的明确“通过”。这些条件同时满足才算该页放行。
- subagent 死亡 = 上下文全无。任何出错重试，旧 session 失去价值，**必须整页打回重跑（详见 Section 7）**。

### 6.9 Step 5 交付

双管线（PNG/SVG）并行；导出失败只回退导出，不回退内容生产。命令见 cheatsheet Step 5。

## 7. 重试与恢复

**原则：只信文件与 Gate 校验，不信口头记忆或 session 状态。**

### 7.1 Step 4 重试（两步走）

**第一步：侦查** — 扫描所有页，收集触发条件（任一成立）的页号：
- `planningN.json` 不存在、为空或 `planning_validator` 不通过
- `slide-N.html` 不存在或为空
- `slide-N.png` 不存在或为空
- `visual_qa.py` 退出码为 1（致命缺陷）
- 主 agent 亲自看图发现明显视觉问题
- 用户在 `review` 后强制人工图审卡口明确表示未通过
- 同类 `P0 / P1` 问题连续 2 轮不收敛，需要回退 `planning`

**第二步：并行重跑** — 收集完毕后，一次性并行启动所有失败页：清三件套及 review 图片残留 → 从 `P4.NN.01` 开始重跑（先生成 prompt，再创建 PageAgent，随后 RUN orchestrator）。

若失败来源只是 `review` 后人工图审未通过，主 agent 默认不要整页从头重跑，而是保留现有 planning/html，显式改用 `PagePatchAgent-N` 从 `review` 重开；只有用户明确要求改结构，或多轮 `review` 修复仍无效，才退回 `html/planning` 或整页重跑。若已经触发“同类 P0 / P1 连续 2 轮不收敛”，则不再允许继续打补丁，必须退回 `planning` 重新冻结预算与骨架。最终放行标准仍与完整 Step 4 完全一致。

单页连续 3 次失败 → 标记 `BLOCKED_PAGE_N`，先跳过推进其余页，最后集中处理。

**BLOCKED 页终态处理**：所有非 BLOCKED 页完成后，主 agent 必须：
1. 向用户汇报被 BLOCKED 的页号及每次失败的 Gate 错误摘要
2. 由用户裁决：**手动修复**（用户自行编辑 HTML）/ **简化重试**（降低该页设计复杂度后重跑）/ **跳过该页**（从 outline 和最终交付中移除）
3. 禁止静默吞掉 BLOCKED 页继续交付

### 7.2 跨对话断点恢复

触发：用户说「继续/恢复」并提供 RUN_ID（或默认取最新目录）。

1. `update_plan` 重建 canonical plan；绑定旧 RUN_ID
2. 里程碑探测（从高到低，第一个 exit=0 为最高自动通过点）：

```bash
contract_validator.py delivery-manifest ...                  # P5
planning_validator.py ...                                    # P4 自动下限（恢复后仍需补跑 visual_qa + 看图）
contract_validator.py style ...                              # P3.5
contract_validator.py outline ...                            # P3
contract_validator.py search-brief ... | source-brief ...   # P2
contract_validator.py requirements-interview ...             # P0/P1
```

3. 从下一未完成 step 继续；前序 Gate 失败则回退重做
4. Step 4：读 `outline.txt` 确认总页数 → 侦查所有页三件套 + `planning_validator` + `visual_qa` → 并行重跑失败页；自动项通过后，主 agent 仍需重新看图确认（旧 session 全部失效）
5. 若 `requirements-interview.txt` 中记录了人工审计开启，恢复到 Step 4 时还必须把最近可用的 runtime prompt、最终 PNG 和 `review/roundX` 存档一并纳入断点材料；如果最近一轮 `review` 后还没有用户明确“通过人工图审”的记录，必须先恢复到这个强制 `[WAIT_USER]` 卡口，再决定是放行还是走 `PagePatchAgent-N`

**禁止**：依赖旧 session、跳过侦查、串行逐页处理、恢复时新建 RUN_ID（除非用户要求全新开始）。
