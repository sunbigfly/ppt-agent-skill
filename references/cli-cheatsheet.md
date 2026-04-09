# CLI 速查表

> 按步骤组织的完整命令手册。执行时用实际路径替换 `SKILL_DIR` / `OUTPUT_DIR` 等变量。
> 主 agent 进入 Step 0 前必须读取此文件建立接口认知。禁止对任何脚本跑 `--help`。

---

## Step 0 采访

Prompt 生成（按能力二选一）：

**A. Structured UI 模式**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-interview-structured-ui.md \
  --var TOPIC="用户主题" \
  --var USER_CONTEXT="用户已提供的背景信息" \
  --inject-file INTERVIEW_MODE_MODULE=SKILL_DIR/references/prompts/module-structured-interview-ui.md \
  --inject-file INTERVIEW_CORE=SKILL_DIR/references/prompts/tpl-interview.md \
  --output OUTPUT_DIR/runtime/prompt-interview.md
```

**B. Text Fallback 模式**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-interview-text-fallback.md \
  --var TOPIC="用户主题" \
  --var USER_CONTEXT="用户已提供的背景信息" \
  --inject-file INTERVIEW_MODE_MODULE=SKILL_DIR/references/prompts/module-text-interview-fallback.md \
  --inject-file INTERVIEW_CORE=SKILL_DIR/references/prompts/tpl-interview.md \
  --output OUTPUT_DIR/runtime/prompt-interview.md
```

执行规则：

1. 先根据 `## 采访 UI 能力` 结论判断当前模式：`structured-ui` 或 `text-fallback`
2. Structured UI 模式使用 A 命令；Text Fallback 模式使用 B 命令
3. 两种模式都必须先生成 `OUTPUT_DIR/runtime/prompt-interview.md`
4. Text Fallback 模式也必须输出分组明确的 Markdown 采访单，不得退化成单行填空或散乱追问
5. 仅当 `prompt_harness.py` 在 Step 0 发生真实接口故障，并已判定 `BLOCKED_SCRIPT_INTERFACE` 时，才允许完全绕过 `prompt-interview.md` 直接发问；覆盖维度不得低于 `tpl-interview.md`

Gate 校验：

```bash
python3 SKILL_DIR/scripts/contract_validator.py interview OUTPUT_DIR/interview-qa.txt
python3 SKILL_DIR/scripts/contract_validator.py requirements-interview OUTPUT_DIR/requirements-interview.txt
```

---

## Step 1 分支确认

主 agent 直接执行（无 subagent）：

1. 识别用户是否已提供现成资料（文件/文本/pptx）
2. 向用户确认分支选择：
   - **research 分支**：联网搜索后制作（→ Step 2A）
   - **非 research 分支**：基于用户现有资料制作（→ Step 2B）
3. 回填 `requirements-interview.txt` 中的 `分支` 字段：

```bash
# 用实际分支值替换 BRANCH_VALUE（research 或 非research）
# 直接在文件中找到 "- 分支：" 这一行并更新它
```

Gate 校验：

```bash
python3 SKILL_DIR/scripts/contract_validator.py requirements-interview OUTPUT_DIR/requirements-interview.txt
```

---

## Step 2A Research（渐进式上下文注入）

> **Subagent 强制**：本步产物必须由 ResearchSynth subagent 生成，主 agent 禁止内联生产。
> subagent 内部自主按阶段渐进：搜索 -> 数据格式化+整理+自审。

**1. 生成阶段 prompt 文件（主 agent 执行）：**

```bash
# Phase 1: 搜索与搜集
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-research-synth-phase1.md \
  --var TOPIC="主题" \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var SEARCH_OUTPUT=OUTPUT_DIR/search.txt \
  --var TOOLS_AVAILABLE="由主 agent 根据感知结果动态填入可用的检索工具及其功能简述" \
  --var MAX_SEARCH_ROUNDS="主 agent 根据主题复杂度预估：简单2/中等3/高复杂4" \
  --var TARGET_PAGES="目标页数（来自采访）" \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/research-phase1-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-research-phase1.md

# Phase 2: 数据格式化、整理与自审
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-research-synth-phase2.md \
  --var SEARCH_OUTPUT=OUTPUT_DIR/search.txt \
  --var BRIEF_OUTPUT=OUTPUT_DIR/search-brief.txt \
  --var TARGET_PAGES="目标页数（来自采访）" \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/research-phase2-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-research-phase2.md
```

**2. 生成 orchestrator 调度 prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-research-synth-orchestrator.md \
  --var PHASE1_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-research-phase1.md \
  --var PHASE2_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-research-phase2.md \
  --var SEARCH_OUTPUT=OUTPUT_DIR/search.txt \
  --var BRIEF_OUTPUT=OUTPUT_DIR/search-brief.txt \
  --output OUTPUT_DIR/runtime/prompt-research-orchestrator.md
```

**3. 创建 Subagent 并执行：**

```
{{SUBAGENT_NAME}} = ResearchSynth
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-research-orchestrator.md
```

> subagent 内部会自主渐进：先读 phase1 完成搜索 -> 再读 phase2 完成格式化+自审 -> FINALIZE

**4. Gate 校验（主 agent 复检）：**

```bash
python3 SKILL_DIR/scripts/contract_validator.py search OUTPUT_DIR/search.txt
python3 SKILL_DIR/scripts/contract_validator.py search-brief OUTPUT_DIR/search-brief.txt
```

> `CURRENT_BRIEF_PATH`（后续步骤用）= `OUTPUT_DIR/search-brief.txt`

若 Gate 已过但素材仍明显单薄，**回退 Step 2A.01**：重新生成 phase1/phase2/orchestrator prompt（扩大 `TOOLS_AVAILABLE`、查询维度或 `MAX_SEARCH_ROUNDS`），并新建 ResearchSynth。**不要**在已 FINALIZE 的旧 session 上继续补搜。

---


## Step 2B 非 Search 分支（渐进式上下文注入）

> **Subagent 强制**：本步产物必须由 SourceSynth subagent 生成，主 agent 禁止内联生产。
> subagent 内部自主按阶段渐进：资料读取+提炼 -> 质量自审+边界校验。

**1. 生成阶段 prompt 文件（主 agent 执行）：**

```bash
# Phase 1: 资料读取与结构化提炼
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-source-synth-phase1.md \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var SOURCE_INPUT=用户资料路径（目录或文件） \
  --var BRIEF_OUTPUT=OUTPUT_DIR/source-brief.txt \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/source-phase1-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-source-phase1.md

# Phase 2: 质量自审与边界校验
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-source-synth-phase2.md \
  --var BRIEF_OUTPUT=OUTPUT_DIR/source-brief.txt \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/source-phase2-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-source-phase2.md
```

**2. 生成 orchestrator 调度 prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-source-synth-orchestrator.md \
  --var PHASE1_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-source-phase1.md \
  --var PHASE2_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-source-phase2.md \
  --var BRIEF_OUTPUT=OUTPUT_DIR/source-brief.txt \
  --output OUTPUT_DIR/runtime/prompt-source-orchestrator.md
```

**3. 创建 Subagent 并执行：**

```
{{SUBAGENT_NAME}} = SourceSynth
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-source-orchestrator.md
```

> subagent 内部会自主渐进：先读 phase1 完成资料提炼 -> 再读 phase2 完成自审 -> FINALIZE

**4. Gate 校验（主 agent 复检）：**

```bash
python3 SKILL_DIR/scripts/contract_validator.py source-brief OUTPUT_DIR/source-brief.txt
```

> `CURRENT_BRIEF_PATH`（后续步骤用）= `OUTPUT_DIR/source-brief.txt`



## Step 3 大纲（渐进式上下文注入）

> **Subagent 强制**：本步产物必须由 Outline subagent 生成，主 agent 禁止内联生产。
> subagent 内部自主按阶段渐进：大纲编写 -> 严格自审+修复。

**1. 生成阶段 prompt 文件（主 agent 执行）：**

```bash
# Phase 1: 大纲编写
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-outline-phase1.md \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var BRIEF_PATH=CURRENT_BRIEF_PATH \
  --var OUTLINE_OUTPUT=OUTPUT_DIR/outline.txt \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/outline-phase1-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-outline-phase1.md

# Phase 2: 严格自审与修复
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-outline-phase2.md \
  --var OUTLINE_OUTPUT=OUTPUT_DIR/outline.txt \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var BRIEF_PATH=CURRENT_BRIEF_PATH \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/outline-phase2-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-outline-phase2.md
```

**2. 生成 orchestrator 调度 prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-outline-orchestrator.md \
  --var PHASE1_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-outline-phase1.md \
  --var PHASE2_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-outline-phase2.md \
  --var OUTLINE_OUTPUT=OUTPUT_DIR/outline.txt \
  --output OUTPUT_DIR/runtime/prompt-outline-orchestrator.md
```

**3. 创建 Subagent 并执行：**

```
{{SUBAGENT_NAME}} = Outline
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-outline-orchestrator.md
```

> subagent 内部会自主渐进：先读 phase1 完成大纲编写 -> 再读 phase2 完成自审修复 -> FINALIZE

**4. Gate 校验（主 agent 复检）：**

```bash
python3 SKILL_DIR/scripts/contract_validator.py outline OUTPUT_DIR/outline.txt
```

若 validator 未通过，回退 Step 3.01 重新生成 prompt 并**重建新的 Outline subagent**；不要复用已 FINALIZE 的旧 session。

---

## Step 3.5 风格（渐进式上下文注入）

> **Subagent 强制**：本步产物必须由 Style subagent 生成，主 agent 禁止内联生产。
> subagent 内部自主按阶段渐进：约束提炼+风格输出 -> 字段合同自审。

**1. 生成阶段 prompt 文件（主 agent 执行）：**

```bash
# Phase 1: 约束提炼与风格输出
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-style-phase1.md \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var OUTLINE_PATH=OUTPUT_DIR/outline.txt \
  --var SKILL_DIR='$SKILL_DIR' \
  --var STYLE_OUTPUT=OUTPUT_DIR/style.json \
  --inject-file STYLE_RUNTIME_RULES=SKILL_DIR/references/styles/runtime-style-rules.md \
  --inject-file STYLE_PRESET_INDEX=SKILL_DIR/references/styles/runtime-style-palette-index.md \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/style-phase1-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-style-phase1.md

# Phase 2: 字段合同自审
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-style-phase2.md \
  --var STYLE_OUTPUT=OUTPUT_DIR/style.json \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/style-phase2-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-style-phase2.md
```

**2. 生成 orchestrator 调度 prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/tpl-style-orchestrator.md \
  --var PHASE1_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-style-phase1.md \
  --var PHASE2_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-style-phase2.md \
  --var STYLE_OUTPUT=OUTPUT_DIR/style.json \
  --output OUTPUT_DIR/runtime/prompt-style-orchestrator.md
```

**3. 创建 Subagent 并执行：**

```
{{SUBAGENT_NAME}} = Style
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-style-orchestrator.md
```

> subagent 内部会自主渐进：先读 phase1 完成风格决策 -> 再读 phase2 完成自审 -> FINALIZE

**4. Gate 校验（主 agent 复检）：**

```bash
python3 SKILL_DIR/scripts/contract_validator.py style OUTPUT_DIR/style.json
```

若 validator 未通过，回退 Step 3.5.01 重新生成 prompt 并**重建新的 Style subagent**；不要复用已 FINALIZE 的旧 session。

---

## Step 4 单页生产（渐进式上下文注入）

> **统一执行后端**：所有环境统一使用 orchestrator 渐进式披露。
> subagent 内部自主按阶段读取 prompt，主 agent 只负责生成 prompt + 创建 subagent + 回收校验。
> 若用户开启人工审计断点，则主 agent 仍先生成同一套 runtime prompt，再按需要创建阶段型 PageAgent 或 `PagePatchAgent-N`。

---

### 4.1 生成 Planning 快照 + 三份阶段 prompt 文件

先生成 planning 阶段会直接用到的 runtime 快照，再依次执行三个 harness 命令（顺序不可调换）：

**4A.0 Planning 图片清单快照：**

```bash
python3 SKILL_DIR/scripts/resource_loader.py images \
  --images-dir OUTPUT_DIR/images \
  --output OUTPUT_DIR/runtime/page-images-N.md
```

**4A.1 Planning 菜单快照：**

```bash
python3 SKILL_DIR/scripts/resource_loader.py menu \
  --refs-dir SKILL_DIR/references \
  --output OUTPUT_DIR/runtime/page-planning-menu-N.md
```

**4A. Planning prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-planning.md \
  --var PAGE_NUM=N \
  --var TOTAL_PAGES=TOTAL \
  --var REQUIREMENTS_PATH=OUTPUT_DIR/requirements-interview.txt \
  --var OUTLINE_PATH=OUTPUT_DIR/outline.txt \
  --var BRIEF_PATH=CURRENT_BRIEF_PATH \
  --var STYLE_PATH=OUTPUT_DIR/style.json \
  --var IMAGES_DIR=OUTPUT_DIR/images \
  --var IMAGE_INVENTORY_PATH=OUTPUT_DIR/runtime/page-images-N.md \
  --var RESOURCE_MENU_PATH=OUTPUT_DIR/runtime/page-planning-menu-N.md \
  --var PLANNING_RUNTIME_COPY_PATH=OUTPUT_DIR/runtime/page-planning-output-N.json \
  --var PLANNING_VALIDATOR_REPORT_PATH=OUTPUT_DIR/runtime/page-planning-validator-N.json \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SUBAGENT_LOG_PATH=OUTPUT_DIR/runtime/page-agent-N.log \
  --var SUBAGENT_NAME=PageAgent-N \
  --var SKILL_DIR='$SKILL_DIR' \
  --var REFS_DIR='$SKILL_DIR/references' \
  --inject-file PRINCIPLES_CHEATSHEET=SKILL_DIR/references/principles/design-principles-cheatsheet.md \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/step4/page-planning-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-page-planning-N.md
```

**4B. HTML prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-html.md \
  --var PAGE_NUM=N \
  --var TOTAL_PAGES=TOTAL \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SLIDE_OUTPUT=OUTPUT_DIR/slides/slide-N.html \
  --var IMAGES_DIR=OUTPUT_DIR/images \
  --var IMAGE_INVENTORY_PATH=OUTPUT_DIR/runtime/page-images-N.md \
  --var HTML_RESOLVE_PATH=OUTPUT_DIR/runtime/page-html-resolve-N.md \
  --var HTML_RUNTIME_COPY_PATH=OUTPUT_DIR/runtime/page-html-output-N.html \
  --var STYLE_PATH=OUTPUT_DIR/style.json \
  --var SUBAGENT_LOG_PATH=OUTPUT_DIR/runtime/page-agent-N.log \
  --var SUBAGENT_NAME=PageAgent-N \
  --var SKILL_DIR='$SKILL_DIR' \
  --var REFS_DIR='$SKILL_DIR/references' \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/step4/page-html-playbook.md \
  --output OUTPUT_DIR/runtime/prompt-page-html-N.md
```

**4C. Review prompt：**

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-review.md \
  --var PAGE_NUM=N \
  --var TOTAL_PAGES=TOTAL \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SLIDE_OUTPUT=OUTPUT_DIR/slides/slide-N.html \
  --var PNG_OUTPUT=OUTPUT_DIR/png/slide-N.png \
  --var REVIEW_DIR=OUTPUT_DIR/review \
  --var REVIEW_RUNTIME_PNG_PATH=OUTPUT_DIR/runtime/page-review-output-N.png \
  --var VISUAL_QA_REPORT_PATH=OUTPUT_DIR/runtime/page-review-qa-N.txt \
  --var STYLE_PATH=OUTPUT_DIR/style.json \
  --var SUBAGENT_LOG_PATH=OUTPUT_DIR/runtime/page-agent-N.log \
  --var SUBAGENT_NAME=PageAgent-N \
  --var SKILL_DIR='$SKILL_DIR' \
  --inject-file PRINCIPLES_CHEATSHEET=SKILL_DIR/references/principles/design-principles-cheatsheet.md \
  --inject-file PLAYBOOK=SKILL_DIR/references/playbooks/step4/page-review-playbook.md \
  --inject-file FAILURE_MODES=SKILL_DIR/references/principles/runtime-failure-modes.md \
  --output OUTPUT_DIR/runtime/prompt-page-review-N.md
```

---

### 4.2 生成 orchestrator 调度 prompt

```bash
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-orchestrator.md \
  --var PAGE_NUM=N \
  --var TOTAL_PAGES=TOTAL \
  --var PLANNING_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-planning-N.md \
  --var HTML_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-html-N.md \
  --var REVIEW_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-review-N.md \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SLIDE_OUTPUT=OUTPUT_DIR/slides/slide-N.html \
  --var PNG_OUTPUT=OUTPUT_DIR/png/slide-N.png \
  --var SUBAGENT_LOG_PATH=OUTPUT_DIR/runtime/page-agent-N.log \
  --var SUBAGENT_NAME=PageAgent-N \
  --var SKILL_DIR='$SKILL_DIR' \
  --output OUTPUT_DIR/runtime/prompt-page-orchestrator-N.md
```

---

### 4.3 创建 PageAgent-N 并执行

回查《Subagent 操作手册》取出调用模板，替换变量后**显式输出到对话**再执行：
```
{{SUBAGENT_NAME}} = PageAgent-N
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-page-orchestrator-N.md
```
> subagent 是完全隔离的：它只能看到 orchestrator prompt 的内容，内部按 orchestrator 指示自主渐进读取各阶段 prompt。

> subagent 内部会按 orchestrator 的指示自主渐进：
> 1. 先读 planning prompt -> 完成策划 -> 产出 planningN.json
> 2. 自主读 html prompt -> 完成设计稿 -> 产出 slide-N.html
> 3. 自主读 review prompt -> 截图审查修复（保底 2 轮）-> 产出 slide-N.png
> 4. P0+P1 清零 + visual_qa 通过后 FINALIZE

---

### 4.3A 可选：人工审计断点 / Step 4 外挂返工

当 Step 0 已记录 `manual_audit_mode != off`，或用户在运行中明确要求“看某张图 / 用 runtime / 从某节点重开”时，主 agent 应切到这一支。

**适用场景：**

- 用户想先看 `planningN.json` 再决定是否继续
- 用户想看当前 `slide-N.html` 或最终 `slide-N.png`
- 用户点名某张 `review/roundX/slide-N.png`
- 用户给出追加 prompt，要求从 `planning` / `html` / `review` 某个节点重新执行

**1. 生成外挂 orchestrator prompt：**

```bash
# 1a. 先生成返工请求并校验
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-audit-request.md \
  --var PAGE_NUM=N \
  --var START_STAGE=html \
  --var END_STAGE=review \
  --var USER_AUDIT_REQUEST="用户追加的图审或改稿要求（压成一行）" \
  --var TARGET_ASSET_PATH=OUTPUT_DIR/review/round2/slide-N.png \
  --var RUNTIME_CONTEXT_PATHS="OUTPUT_DIR/runtime/prompt-page-html-N.md; OUTPUT_DIR/runtime/prompt-page-review-N.md; OUTPUT_DIR/runtime/page-html-resolve-N.md; OUTPUT_DIR/runtime/page-html-output-N.html" \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SLIDE_OUTPUT=OUTPUT_DIR/slides/slide-N.html \
  --var PNG_OUTPUT=OUTPUT_DIR/png/slide-N.png \
  --output OUTPUT_DIR/runtime/page-audit-request-N.txt

python3 SKILL_DIR/scripts/contract_validator.py page-audit-request OUTPUT_DIR/runtime/page-audit-request-N.txt --base-dir OUTPUT_DIR

# 1b. 再生成外挂 orchestrator prompt
python3 SKILL_DIR/scripts/prompt_harness.py \
  --template SKILL_DIR/references/prompts/step4/tpl-page-breakpoint-orchestrator.md \
  --var PAGE_NUM=N \
  --var TOTAL_PAGES=TOTAL \
  --var AUDIT_REQUEST_PATH=OUTPUT_DIR/runtime/page-audit-request-N.txt \
  --var START_STAGE=html \
  --var END_STAGE=review \
  --var PLANNING_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-planning-N.md \
  --var HTML_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-html-N.md \
  --var REVIEW_PROMPT_PATH=OUTPUT_DIR/runtime/prompt-page-review-N.md \
  --var PLANNING_OUTPUT=OUTPUT_DIR/planning/planningN.json \
  --var SLIDE_OUTPUT=OUTPUT_DIR/slides/slide-N.html \
  --var PNG_OUTPUT=OUTPUT_DIR/png/slide-N.png \
  --var SUBAGENT_LOG_PATH=OUTPUT_DIR/runtime/page-patch-agent-N.log \
  --var SUBAGENT_NAME=PagePatchAgent-N \
  --var SKILL_DIR='$SKILL_DIR' \
  --var TARGET_ASSET_PATH=OUTPUT_DIR/review/round2/slide-N.png \
  --var RUNTIME_CONTEXT_PATHS="OUTPUT_DIR/runtime/prompt-page-html-N.md; OUTPUT_DIR/runtime/prompt-page-review-N.md" \
  --var USER_AUDIT_REQUEST="用户追加的图审或改稿要求" \
  --output OUTPUT_DIR/runtime/prompt-page-breakpoint-N.md
```

> 若当前没有点名图片或额外 runtime 文件，将 `TARGET_ASSET_PATH` 或 `RUNTIME_CONTEXT_PATHS` 填成 `none`。

**2. 创建 `PagePatchAgent-N` 并执行：**

```
{{SUBAGENT_NAME}} = PagePatchAgent-N
{{MODEL}}           = SUBAGENT_MODEL
{{THINKING_EFFORT}} = SUBAGENT_THINKING_EFFORT
{{PROMPT_PATH}}   = OUTPUT_DIR/runtime/prompt-page-breakpoint-N.md
```

**3. 起点规则：**

- `START_STAGE=planning`：重做策划，并继续跑 `html -> review`
- `START_STAGE=html`：复用现有 planning，重做 `html -> review`
- `START_STAGE=review`：复用现有 planning + html，直接进图审修复并重新截图

**4. 终点规则：**

- `END_STAGE=planning`：只产出更新后的 `planningN.json`，用于中间断点确认
- `END_STAGE=html`：产出更新后的 `slide-N.html`，用于中间断点确认
- `END_STAGE=review`：产出更新后的 `slide-N.png`，随后仍要进入 4.4 的整页终检

---

### 4.4 回收 FINALIZE — 主 agent 整页终检

**第 1 步：产物存在性 + 合同校验**

```bash
test -s OUTPUT_DIR/planning/planningN.json
python3 SKILL_DIR/scripts/planning_validator.py OUTPUT_DIR/planning --refs SKILL_DIR/references --page N
test -s OUTPUT_DIR/slides/slide-N.html
test -s OUTPUT_DIR/png/slide-N.png
```

**第 2 步：自动化视觉断言（第一道过滤器）**

```bash
python3 SKILL_DIR/scripts/visual_qa.py OUTPUT_DIR/png/slide-N.png --planning OUTPUT_DIR/planning/planningN.json --html OUTPUT_DIR/slides/slide-N.html
# exit=1 -> 致命缺陷，直接重跑
# exit=2 -> 品质警告，第 3 步看图时重点关注 WARN 项
```

**第 3 步（核心质量关卡）：主 agent 亲自看截图**

> 这是整个质量体系的最终防线。`visual_qa.py` 只能抓硬伤，排版质量、内容完整性、视觉和谐度必须由主 agent 亲眼确认。

1. 用当前宿主可用的图像查看能力查看 `OUTPUT_DIR/png/slide-N.png`
2. 重点关注：
   - 文字是否可读、排版是否正常（竖排单字列、文字溢出截断等）
   - 卡片内容是否完整（对照 subagent FINALIZE 中的 planning 卡片列表）
   - 整体视觉是否和谐（不像毛坯房、不像默认 HTML）
   - visual_qa.py 输出的 WARN 项是否确实有问题
3. 如果看到明显问题 -> 标记该页失败，触发重跑

**判定规则**：若 `visual_qa exit=1` 或主 agent 看图发现明显问题，则本页视为失败，触发整页重跑。

---

**触发条件（任一成立）：**
- `planningN.json` 不存在、为空或 `planning_validator.py` 不通过
- `slide-N.html` 不存在或为空
- `slide-N.png` 不存在或为空
- `visual_qa.py` 退出码为 1（致命缺陷）
- 主 agent 亲自看图发现明显视觉问题

**无论同对话还是跨对话，统一两步走：**

**第一步：侦查** -- 读 `outline.txt` 确认总页数，遍历所有页收集失败页列表：

```bash
# 对每页 1..N：
test -s OUTPUT_DIR/planning/planningN.json && \
test -s OUTPUT_DIR/slides/slide-N.html && \
test -s OUTPUT_DIR/png/slide-N.png && \
python3 SKILL_DIR/scripts/planning_validator.py OUTPUT_DIR/planning --refs SKILL_DIR/references --page N && \
python3 SKILL_DIR/scripts/visual_qa.py OUTPUT_DIR/png/slide-N.png --planning OUTPUT_DIR/planning/planningN.json --html OUTPUT_DIR/slides/slide-N.html
# 任一 exit!=0 -> 加入失败页列表
```

> 自动探测通过后，主 agent 仍需重新看图确认；`visual_qa.py` 不是人工审美检查的替代品。

**第二步：并行重跑** -- 收集完毕，一次性并行启动所有失败页（不串行逐页）：

```bash
# 对失败页列表 [N1, N2, ...] 中每页，清理旧产物及可能的 review 图片残留：
python3 -c "import os, glob; [os.remove(p) for p in ['OUTPUT_DIR/planning/planningN.json','OUTPUT_DIR/slides/slide-N.html','OUTPUT_DIR/png/slide-N.png'] + glob.glob('OUTPUT_DIR/review/round*/slide-N.png') if os.path.exists(p)]"
# 从 Step 4 的 prompt 生成阶段开始重跑：先生成 prompt，再创建 PageAgent-N，随后 RUN orchestrator
```

> session 一律视为不可续接（subagent 死亡=上下文全无），整页从 4.1 开始重跑。
> 跨对话恢复时旧 session 全部失效，逻辑相同。

---

## Step 5 导出

执行管线：

```bash
# 1. 预览
python3 SKILL_DIR/scripts/html_packager.py OUTPUT_DIR/slides -o OUTPUT_DIR/preview.html

# 2. PNG 管线（与 SVG 并行）
# --scale 3 → 输出 3840x2160 高清 PNG 供 PPT 使用（图审用 0.75 是为省 token，两者目的不同）
python3 SKILL_DIR/scripts/html2png.py OUTPUT_DIR/slides -o OUTPUT_DIR/png --scale 3
python3 SKILL_DIR/scripts/png2pptx.py OUTPUT_DIR/png -o OUTPUT_DIR/presentation-png.pptx

# 3. SVG 管线（与 PNG 并行）
python3 SKILL_DIR/scripts/html2svg.py OUTPUT_DIR/slides -o OUTPUT_DIR/svg
python3 SKILL_DIR/scripts/svg2pptx.py OUTPUT_DIR/svg -o OUTPUT_DIR/presentation-svg.pptx --html-dir OUTPUT_DIR/slides

# 4. 交付清单
# 主 agent 按以下 schema 写入 delivery-manifest.json
```

**delivery-manifest.json 必填 schema**：

```json
{
  "run_id": "RUN_ID（与 OUTPUT_DIR 对应）",
  "generated_at": "ISO 8601 时间戳（如 2026-04-01T14:30:00Z）",
  "summary": {
    "total_pages": 页数（正整数）
  },
  "artifacts": {
    "preview_html": "preview.html（相对于 OUTPUT_DIR 的路径）",
    "presentation_png_pptx": "presentation-png.pptx",
    "presentation_svg_pptx": "presentation-svg.pptx"
  },
  "pages": [
    { "page": 1, "planning": "planning/planning1.json", "html": "slides/slide-1.html", "png": "png/slide-1.png" }
  ]
}
```

> `run_id`、`generated_at`、`artifacts`（含三个路径）为 validator 强制校验字段；`summary` 和 `pages` 建议填写。

Gate 校验：

```bash
python3 SKILL_DIR/scripts/contract_validator.py delivery-manifest OUTPUT_DIR/delivery-manifest.json --base-dir OUTPUT_DIR
```

---

## 资源路由

菜单（planning 阶段）：

```bash
python3 SKILL_DIR/scripts/resource_loader.py menu \
  --refs-dir SKILL_DIR/references \
  --output OUTPUT_DIR/runtime/page-planning-menu-N.md
```

解析（html 阶段）：

```bash
python3 SKILL_DIR/scripts/resource_loader.py resolve --refs-dir SKILL_DIR/references --planning OUTPUT_DIR/planning/planningN.json
```

图片清单（planning / html 阶段）：

```bash
python3 SKILL_DIR/scripts/resource_loader.py images --images-dir OUTPUT_DIR/images
```

---

## 里程碑总验收

```bash
python3 SKILL_DIR/scripts/milestone_check.py <stage> --output-dir OUTPUT_DIR
```

---

## 合同校验器 contract-type 列表

`interview` / `requirements-interview` / `search` / `search-brief` / `source-brief` / `outline` / `style` / `images` / `page-review` / `page-audit-request` / `delivery-manifest`

通用格式：

```bash
python3 SKILL_DIR/scripts/contract_validator.py <contract-type> <target-file> [--base-dir OUTPUT_DIR]
```

---

## 视觉质量断言

> Step 4 回收后的第一道自动过滤器。抓明显硬伤（分辨率、空白、文件损坏等），真正的视觉质量判断由主 agent 亲自看图完成。

单页：

```bash
python3 SKILL_DIR/scripts/visual_qa.py OUTPUT_DIR/png/slide-N.png --planning OUTPUT_DIR/planning/planningN.json --html OUTPUT_DIR/slides/slide-N.html
```

批量：

```bash
python3 SKILL_DIR/scripts/visual_qa.py OUTPUT_DIR/png --planning-dir OUTPUT_DIR/planning --html-dir OUTPUT_DIR/slides
```

退出码：`0` = 全通过、`1` = FAIL（致命缺陷，必须重跑）、`2` = WARN（品质警告，看图复查）

依赖：`pip install Pillow`
