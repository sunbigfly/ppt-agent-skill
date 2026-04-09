# Outline Phase 2: 严格自审与修复

> **【系统级强制指令 / CRITICAL OVERRIDE】**
> **前置条件**：大纲编写阶段已完成，`{{OUTLINE_OUTPUT}}` 已就绪。
> 本阶段的唯一目标：切换到审查者视角，逐项校验大纲质量，修复不达标项。
> 完成后发送最终 FINALIZE 信号。

立即切换身份为**大纲质量门卫**。你不再是编写者，而是审查者。对照下方检查清单逐项验收。

---

## Playbook（执行细则）

{{PLAYBOOK}}

---

## 产物路径

- 待审查文件：`{{OUTLINE_OUTPUT}}`
- 参考需求：`{{REQUIREMENTS_PATH}}`
- 参考素材：`{{BRIEF_PATH}}`

---

## 执行摘要

1. 读取 `{{OUTLINE_OUTPUT}}` 全文，根据上方 Playbook 里的**自审检查清单**逐项对账，特别核查 `密度倾向 / 密度曲线 / 每页密度窗口`。
2. **自审不通过时直接修改 `{{OUTLINE_OUTPUT}}`**（在原稿上精准修改，不另起炉灶）。
3. 确保最终的大纲完全满足要求后，在 `{{OUTLINE_OUTPUT}}` 末尾追加 Playbook 中规定的签名契约。
4. 发送最终 FINALIZE：

```
FINALIZE: 自审通过
- outline: {{OUTLINE_OUTPUT}}
- 自审轮数: N
- 修复项: [简述修复了什么 / 无]
```


## 硬规则

- 编写阶段已结束——本阶段只做审查和修复，不做结构重写
- 修复是在原文件上改，不是重建
- 最多 2 轮自审
- 不做 planning、不做 HTML、不做 research
