# Text Fallback Mode -- 结构化文本采访单

## 强制执行纪律

1. **必须一字不漏复制**：你在发出采访问卷时，**必须且只能 100% 原样复制**下方【固定输出格式】代码块内的 Markdown 文本！
2. **严禁自作聪明的删减和总结**：绝不允许你基于后文的业务逻辑自己编造采访问卷！绝不允许把带有【A. xxx】【B. xxx】的选项列表吃掉退化成分组标题，必须每一行都原封不动吐给用户，否则用户将不知道该选什么。
3. **极致静默**：严禁附加寒暄、前言或“为什么要问”的解释。
4. 若用户直接回复“全部按默认，用 research”，主 agent 必须按默认值归纳并继续推进，不得因此卡死。

## 固定输出格式

```markdown
请按如下清单直接回复（填写序号或补全说明，不确定选“默认”）：

**A. 场景与目标**
- 场景：【A. 严肃内部汇报(对齐目标)】 【B. 重量级产品宣讲(抓眼球)】 【C. 招商/融资路演(秀实力)】 【D. 知识型培训课件(重逻辑)】 【E. 其他:___】
- 身份与受众：【A. 一线操盘手向高层汇报(要资源/讲成效)】 【B. 业务一号位向外部客户布道(画大饼/重利益)】 【C. 技术骨干与硬核同行切磋(扣细节)】 【D. 专业人士向泛大众科普(求易懂)】 【E. 其他:___】
- 目标：【A. 扭转认知/刷新观念】 【B. 促成拍板决策或掏钱】 【C. 吸引对方主动加入/传播】 【D. 纯信息铺陈同步】 【E. 其他:___】

**B. 内容与边界**
- 期望页数：【A. 5-10页(微型/短汇报)】 【B. 10-20页(标准)】 【C. 20-30页及以上(宽幅深度盘点)】 【D. 让AI凭内容自动决断】
- 密度：【A. 极简呼吸感(整套偏松，不代表每页都空)】 【B. 均衡图文(整套有起伏，主次分明)】 【C. 极高密度干货(整套窗口上移，但页与页仍要错落)】
- 资料：【A. Research(全网检索扩写并做发散)】 【B. 严格闭卷(绝不发散，仅限用户现有文字)】
- 核心主张与红线：【自由补充，例如：主张必须是我们最快，禁止提xx竞品名字】

**C. 视觉与资产策略**
- 风格：【A. 蓝灰数据向极简商务】 【B. 赛博/暗色流光科技极客】 【C. 活泼多色的动感/流行风】 【D. 让AI凭主题自决定】 【E. 其他:___】
- 语言：【A. 中文】 【B. 英文】 【C. 中英双语/专业术语多用英文】
- 配图策略：【A. 无脑 Decorate(装饰点缀)】 【B. Generate(让AI做插画/文生图)】 【C. Provide(有指定图库)】 【D. 仅留空占位槽】
- 品牌定制：【自由补充，例如：主色设为 #FF0000】

**D. 架构控制**
- 模型：【A. 默认(继承主代理)】 【B. 指定更强/更快的模型:___】
- 思考深度/推理等级：【A. 默认(中等)】 【B. 低(快速逻辑)】 【C. 高(烧脑深度思考)】

**E. 人工审计与断点**
- 是否参与中间审计：【A. 不参与，自动跑完全程】 【B. 只看关键节点(如大纲/风格/最终图审)】 【C. 细颗粒度断点(可在单页 planning/html/review 介入)】
- 重点介入节点：【A. 只看最终图审图】 【B. 看 HTML + 图审】 【C. planning / HTML / 图审都可介入】 【D. 其他:___】
- 审计材料范围：【A. 只看主 agent 摘要】 【B. 可直接看最终 PNG】 【C. 可直接点名 runtime 文件 / HTML / 某轮审查图】
```

## 归纳后的问答落点

主 agent 收到文本回答后，必须先按 canonical 字段归纳，再归一化写盘：

```text
presentation_scenario -> scenario
core_audience -> audience
visual_style -> style
brand_constraints -> brand
language_mode -> language
imagery_strategy -> imagery
material_strategy -> material_strategy
subagent_model_strategy -> subagent_model_strategy
subagent_thinking_effort -> subagent_thinking_effort
manual_audit_mode -> manual_audit_mode
manual_audit_scope -> manual_audit_scope
manual_audit_assets -> manual_audit_assets
```

若用户回复“全部按默认，用 research”，至少按以下默认落点写入：

```text
material_strategy: research
page_density: 适中
visual_style: 自动匹配
language_mode: 中文
imagery_strategy: decorate
subagent_model_strategy: 继承主代理
subagent_thinking_effort: 中等
manual_audit_mode: off
manual_audit_scope: final_review_only
manual_audit_assets: summary_only
```
