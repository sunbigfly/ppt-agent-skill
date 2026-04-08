# 采访问卷（Text Fallback）

主题：{{TOPIC}}
用户背景：{{USER_CONTEXT}}

---

## 当前执行模式

当前环境不支持原生结构化采访 UI。你必须回退为**结构化文本采访单**，而不是一行填空或散乱追问。

{{INTERVIEW_MODE_MODULE}}

---

## 共享采访核心

{{INTERVIEW_CORE}}

---

## 最终要求

- 直接给用户一个分组明确的 Markdown 采访单
- 不要退化成 `场景=；受众=；目标动作=...` 这种单行格式
- 允许用户写“默认”，但字段覆盖不能少
- 若用户只回“全部按默认，用 research”，仍必须按 shared core 的默认落点补全 `material_strategy: research` 等关键字段
- 收集完成后，主 agent 再写 `interview-qa.txt` 与 `requirements-interview.txt`
- 写 `interview-qa.txt` 时，必须追加 canonical 锚点段，显式写出 `target_action`、`must_avoid`、`material_strategy`、`subagent_model_strategy`、`subagent_thinking_effort`、`manual_audit_mode`、`manual_audit_scope`、`manual_audit_assets` 等关键字段，避免 validator 因用户回答过短而漏检
