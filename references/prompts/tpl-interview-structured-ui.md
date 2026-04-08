# 采访问卷（Structured UI）

主题：{{TOPIC}}
用户背景：{{USER_CONTEXT}}

---

## 当前执行模式

当前环境已确认支持原生结构化采访 UI。你必须优先使用 CLI 自带的结构化提问能力，而不是直接输出长段普通文本问题。

{{INTERVIEW_MODE_MODULE}}

---

## 共享采访核心

{{INTERVIEW_CORE}}

---

## 最终要求

- 优先一次收集高信号维度；若题数受限，可拆成 2 轮
- **必须把** `presentation_scenario`、`core_audience`、`target_action`、`page_density`、`visual_style`、`language_mode`、`imagery_strategy`、`material_strategy`、`manual_audit_mode` 做成带丰富备选项的结构化选择
- 写盘前先按 shared core 的字段映射归一化：`presentation_scenario -> scenario`、`core_audience -> audience`、`visual_style -> style`、`brand_constraints -> brand`、`language_mode -> language`、`imagery_strategy -> imagery`
- 允许用户对开放项自由补充，或是选择“其他”
- 收集完成后，主 agent 再写 `interview-qa.txt` 与 `requirements-interview.txt`
- 写 `interview-qa.txt` 时，必须追加 canonical 锚点段，显式写出 `target_action`、`must_avoid`、`material_strategy`、`subagent_model_strategy`、`subagent_thinking_effort`、`manual_audit_mode`、`manual_audit_scope`、`manual_audit_assets` 等关键字段，避免 validator 因用户回答过短而漏检
