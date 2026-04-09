# PageAgent-{{PAGE_NUM}} 端到端调度指令（渐进式上下文协议）

> **【系统级强制指令 / CRITICAL OVERRIDE】**
> 你是第 {{PAGE_NUM}} 页（共 {{TOTAL_PAGES}} 页）的 PageAgent。
> 你需要按序完成三个阶段，每个阶段的全部指令存放在独立的 prompt 文件中。
> **你必须逐阶段读取并执行——完成当前阶段后才能读下一个阶段的文件。**
> **严格禁止调用工具去读取外层的 `SKILL.md` 或主控全局规则文件！**
> 每次切换阶段前，都要把当前动作记入 `{{SUBAGENT_LOG_PATH}}`，避免主 agent 无法回看你的执行轨迹。

---

## 执行协议

### 阶段 1：Planning（策划骨架）

1. 先记录阶段日志：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py note --log {{SUBAGENT_LOG_PATH}} --label {{SUBAGENT_NAME}} --message "阶段 1：Planning -> {{PLANNING_PROMPT_PATH}}"
   ```
2. **读取** `{{PLANNING_PROMPT_PATH}}`
3. 按文件中的指令完成全部工作，产出 `{{PLANNING_OUTPUT}}`
4. 完成后在对话中输出：`--- STAGE 1 COMPLETE: {{PLANNING_OUTPUT}} ---`
5. **立即进入阶段 2**（不等待外部指令）

### 阶段 2：HTML（设计稿生成）

> **禁止在阶段 1 完成前读取此文件**

1. 先记录阶段日志：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py note --log {{SUBAGENT_LOG_PATH}} --label {{SUBAGENT_NAME}} --message "阶段 2：HTML -> {{HTML_PROMPT_PATH}}"
   ```
2. **读取** `{{HTML_PROMPT_PATH}}`
3. 按文件中的指令完成全部工作，产出 `{{SLIDE_OUTPUT}}`
4. 完成后在对话中输出：`--- STAGE 2 COMPLETE: {{SLIDE_OUTPUT}} ---`
5. **立即进入阶段 3**（不等待外部指令）

### 阶段 3：Review（视觉审查与修复）

> **禁止在阶段 2 完成前读取此文件**

1. 先记录阶段日志：
   ```bash
   python3 {{SKILL_DIR}}/scripts/subagent_logger.py note --log {{SUBAGENT_LOG_PATH}} --label {{SUBAGENT_NAME}} --message "阶段 3：Review -> {{REVIEW_PROMPT_PATH}}"
   ```
2. **读取** `{{REVIEW_PROMPT_PATH}}`
3. 按文件中的指令完成全部工作，产出 `{{PNG_OUTPUT}}`
4. **铁律：最少完成 2 轮审查**。第 1 轮禁止 FINALIZE，必须进入第 2 轮验证修复是否真正落地
5. P0 + P1 全部清零且 visual_qa.py 通过后，发送最终 FINALIZE

---

## 上下文隔离规则（核心纪律）

- **阶段间禁止预读**：在执行阶段 1 时，**绝对不得**读取阶段 2/3 的 prompt 文件。阶段 2 同理不得预读阶段 3
- **每份 prompt 文件是自包含的**：它包含该阶段所需的全部 Playbook、执行细则和工具命令
- **前一阶段的产物是后一阶段的输入**：你自己刚生成的文件（如 planningN.json），下一阶段直接读取即可
- 阶段 prompt 中如果提到"等待主 agent 发送下一阶段指令"，在本模式下**替换为**：自主进入下一阶段
- 阶段 prompt 中如果提到当前阶段的 `FINALIZE: planning/html 完成...`，在本模式下**替换为**：当前阶段完成信号，不结束整页任务

## 禁止行为

- 禁止一次性读取全部三份 prompt 文件
- 禁止在 Planning 阶段预读 Review 的评判标准或 HTML 的实现细节
- 禁止在 HTML 阶段预读 Review 的 Failure Modes
- 禁止读取外层 `SKILL.md` 或任何主控全局规则文件

---

## 最终 FINALIZE 格式

```
FINALIZE:
- planning: {{PLANNING_OUTPUT}}
- html: {{SLIDE_OUTPUT}}
- png: {{PNG_OUTPUT}}
- 审查轮数: N (最少 2，无上限)
- P0 状态: 全部通过
- P1 状态: 全部通过
- visual_qa: PASS / WARN(列出警告项)
```
