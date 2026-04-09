# Scripts Index

本目录包含 PPT 工作流的全部执行脚本。

## 核心调度

| 脚本 | 用途 | 调用方 |
|------|------|--------|
| `prompt_harness.py` | 模板变量填充，生成 subagent prompt | 主 agent |
| `resource_loader.py` | 资源路由器（menu 菜单 / resolve 按需加载 / images 图片清单） | 主 agent + subagent |
| `subagent_logger.py` | 记录 subagent 阶段命令的 stdout/stderr 与阶段注记到 runtime 日志 | subagent |

## 校验工具

| 脚本 | 用途 | 调用方 |
|------|------|--------|
| `contract_validator.py` | 合同校验（`interview` / `requirements-interview` / `search` / `search-brief` / `source-brief` / `outline` / `style` / `images` / `page-review` / `page-audit-request` / `delivery-manifest`） | 主 agent |
| `planning_validator.py` | Step 4 planning JSON 单页/全量验证 | subagent 自审 + 主 agent gate |
| `milestone_check.py` | 按里程碑阶段验收 | 主 agent |
| `check_skill.py` | 检查 markdown / prompt / validator / 资源之间的协议漂移 | skill 作者 / 维护者 |
| `smoke_skill.py` | 跑 Step 3/4 的最小端到端 smoke test（outline/planning validator + visual_qa + resource_loader + prompt_harness） | skill 作者 / 维护者 |

说明：

- `contract_validator.py style` 现已按 runtime style 合同检查 `style_id`、`style_name`、`mood_keywords`、`design_soul`、`variation_strategy`、`decoration_dna`、`css_variables`、`font_family`
- `resource_loader.py` 的 `menu` / `resolve` 会跳过 `runtime-*` 文件；这些文件由主链定向注入
- Step 4 现在会先用 `resource_loader.py menu --output ...` 生成 `runtime/page-planning-menu-N.md`，既给 planning 阶段读取，也方便维护时直接检查
- `check_skill.py` 是维护期自检，不参与运行时调度；建议改完 `tpl` / `playbook` / `cli-cheatsheet` / Step 4 schema 示例后手动跑一次
- `smoke_skill.py` 是维护期冒烟，不参与运行时调度；它会真实调用现有 CLI，验证 Step 0 双模板按能力裁剪、Step 3 三种 `density_bias` 大纲合同、Step 4 五档 `density_label`、`visual_qa` 的 `planning + html` 双层断言、非 `content` 页 `page-templates/` 路由，以及关键资源型 prompt 注入还能接通

## 导出工具

| 脚本 | 用途 |
|------|------|
| `html_packager.py` | 生成 preview.html |
| `html2png.py` | HTML -> PNG 截图 |
| `html2svg.py` | HTML -> SVG 转换 |
| `png2pptx.py` | PNG -> PPTX 导出 |
| `svg2pptx.py` | SVG -> PPTX 导出 |

## 辅助

| 脚本 | 用途 |
|------|------|
| `workflow_versions.py` | 统一 workflow/schema version 常量 |

## 依赖关系

```
prompt_harness.py       -- 独立
resource_loader.py      -- 独立
contract_validator.py   -> planning_validator.py -> workflow_versions.py
milestone_check.py      -- 独立
check_skill.py          -> planning_validator.py + prompt_harness.py
smoke_skill.py          -> planning_validator.py + resource_loader.py + prompt_harness.py
```
