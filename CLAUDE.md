# CLAUDE.md · MCN 脚本助手项目指令

> 这是一份给 Claude Code 看的项目级指令。
> 项目是 AOI 部门 AI Agent 实习的 48 小时实操测试,核心交付物是一个符合 Anthropic Agent Skills 标准的可复用 Skill。

---

## 项目身份

- **项目名:** mcn-script-assistant
- **业务场景:** MCN 商单 - 小红书短视频脚本自动化生成
- **客户 Brief:** 轻醒酸奶 0 蔗糖高蛋白希腊酸奶,目标 22-35 城市女性,平台为小红书短视频,要求自然种草、不能承诺减肥/降糖/治疗
- **截止时间:** 收到题目后 48 小时
- **评分权重:** 业务理解 15% / 调研 15% / **AI 工作流与 Skill 45%** / 交付完整度 25%

## 你的工作边界(很重要)

**你负责 vibe code 的部分:**
- 目录结构搭建
- `skills/mcn-script-assistant/` 下所有文件的脚手架(SKILL.md 由我和你协作迭代,不要单方面终稿)
- 飞书 API Python 脚本(鉴权、写入多维表格)
- 风险质检脚本(违禁词扫描 + LLM-as-Judge)
- Coze 工作流的代码节点片段(数据格式转换函数)
- README、Mermaid 流程图、目录索引
- 单元测试(pytest)
- `.gitignore`、`pyproject.toml`、`.env.example`
- Git commit message(Conventional Commits 格式)

**你不要碰这些(我自己写):**
- `report.md` 里的博主调研内容、四维评分、选择理由 —— 这是 15% 业务判断分,AI 写的会显得通用
- `references/blogger-*.md` 里的博主拆解 —— 我手工总结,你只能帮我做格式化
- SKILL.md 里 frontmatter 的 `description` 字段 —— 决定触发率,我先起草你再优化
- 任何提交给评审的文字成品的"创作"环节 —— 你做润色,不做主创

如果我让你写上面这些,先反问一句"这部分是不是应该由我写主稿?",确认后再动。

---

## 技术栈与规范

**Python**
- 用 `uv` 管理依赖,不用 pip/poetry。`uv init` 起项目,`uv add` 加包
- Python 3.11+,所有函数加类型注解
- LLM 输入输出必须用 Pydantic Model 定义 schema,不接受裸 dict
- 配置项一律走 `python-dotenv` + `.env`,代码里禁止 hardcode 任何 key/token
- 依赖只装真正需要的:`requests`、`python-dotenv`、`pydantic`、`pytest`。不要装 langchain、不要装 openai sdk(我们用 anthropic 和 deepseek,直接 requests 就够)

**LLM 调用**
- 主力模型:`claude-sonnet-4-6`(API 名 `claude-sonnet-4-6`)。重大架构决策时切到 Opus 4.7
- Coze 工作流内的脚本生成用 DeepSeek-V3(免费)
- 质检的 LLM-as-Judge 用 `claude-haiku-4-5-20251001`(便宜快)
- **不要直接调 LLM 写死模型名**,模型名必须从 `.env` 或函数参数传入,方便切换

**飞书**
- 优先方案:Coze 飞书多维表格插件(我手动配,你不用碰)
- 兜底方案:`feishu/write_to_feishu.py` Python 直连。你写这个脚本时:
  - 鉴权拿 `tenant_access_token`,缓存到内存,2 小时过期才重取
  - 写入用 bitable v1 的 `add_records` 批量接口,不要单条循环
  - 所有 HTTP 调用包一层 `try/except`,失败记 log,返回结构化 error
  - 给评审跑的 demo 加一个 `--dry-run` 参数,不真的写飞书

**测试**
- 关键脚本(违禁词扫描、飞书写入、Skill 输出格式校验)必须有 pytest 测试
- 测试用 fixtures,不要在测试代码里写真实的 brief 全文
- 提交前跑 `uv run pytest`,所有绿才 commit

**Git**
- Conventional Commits:`feat:`、`fix:`、`docs:`、`test:`、`chore:`、`refactor:`
- 一次 commit 只做一件事,不要把 Skill 改动和飞书脚本混在一起
- commit message 写中文或英文都行,但同一个仓库保持一致(我倾向英文)
- **不要 push** —— 你只在本地 commit,push 由我手动做

**文件**
- 所有路径相对于仓库根目录
- 中间产物(调试日志、tmp 文件)放 `.tmp/`,加进 `.gitignore`
- 评审能看到的目录结构必须严格按规划文档里的样子

---

## 安全红线

绝对不做的事:
1. 不在代码、commit、log 里出现任何真实 API Key、`app_secret`、`tenant_access_token`
2. 不调用任何小红书爬虫(MediaCrawler、Spider_XHS 等)。博主数据由我人工提供截图和文字
3. 不写"绕过反爬"、"模拟登录"、"自动获取小红书 cookie"类代码
4. 不在脚本里 hardcode 任何博主真实昵称、用户 ID 之外的隐私信息
5. 任何要往飞书真实写数据的脚本,默认 `dry-run=True`,需要显式传 `--commit` 才真写
6. 评审用的飞书表格分享链接由我手动生成,你不要在代码里调用"修改文档权限"接口

如果某个任务你觉得碰到了上面的边界,停下来问我,不要自己拍板。

---

## 任务执行风格

**优先级:**
对每个任务先按这个顺序判断:
1. 这件事属于"我自己写"还是"vibe code"?属于前者就反问。
2. 已有的代码能不能直接复用或微调?能复用就不要重写。
3. 是不是先写一个最小可跑通的版本(MVP)?先跑通,再迭代。
4. 单元测试同步写,不要拖到最后。

**沟通节奏:**
- 大改动前先说计划,不要直接动 5 个文件
- 长任务(>5 步)中途汇报一次进度
- 遇到模糊点,优先问我,不要自己脑补需求
- 完成后用 3-5 句话总结你做了什么、动了哪些文件、有没有遗留问题

**反内卷:**
- 不要给文件加华丽的 emoji header。Markdown 用清晰的层级即可
- 不要写"这是一个 AI 生成的文件"或类似声明
- 注释只写"为什么",不写"是什么"——代码自身能表达"是什么"
- 不要为了显得专业去引入复杂依赖(比如不要为了校验 JSON 装一堆库)
- README 段首不要写 "🚀 Welcome to..." 这种空话开头

---

## 跑通顺序参考

如果我没说从哪开始,你自己判断的话按这个顺序:
1. `uv init` + `pyproject.toml` + `.env.example` + `.gitignore`
2. 目录骨架 `mkdir -p` 一次到位
3. `feishu/write_to_feishu.py`(因为飞书联调最容易踩坑,先把通路打通)
4. `skills/mcn-script-assistant/scripts/risk_check.py`(质检脚本)
5. `skills/mcn-script-assistant/references/forbidden_words.md`(违禁词库)
6. `tests/`(测试)
7. Mermaid 工作流图
8. README 草稿(等我把 SKILL.md 写完之后再补完)

每完成一步,自检:
- 有没有 hardcode 敏感信息?
- 有没有跑 pytest?
- commit message 是不是 Conventional?

---

## 关于 Skill 本身

`SKILL.md` 是这个项目最贵的交付物,所以执行规则不一样:
- 我会先放一份 v1 草稿在 `skills/mcn-script-assistant/SKILL.md`
- 你的工作是:阅读它,然后只做这三类操作
  1. 指出 frontmatter 的 description 是否符合 Anthropic 官方"pushy 触发"风格,给修改建议(我决定改不改)
  2. 检查文档结构是否符合 agentskills.io 规范
  3. 帮我写 `references/` 里被引用的辅助文档(违禁词库、博主档案模板、输出 JSON Schema)和 `scripts/` 里的执行脚本
- **不要直接重写 SKILL.md 主体内容**,除非我明确说"重写"

---

## 当前阶段

(这里我会随项目进展更新,你每次启动先看)

阶段:**[集成 + 端到端验证]**

已完成:
- 脚手架(uv / 目录 / .env / .gitignore)
- skills/mcn-script-assistant/ canonical 落位:SKILL.md / eval-results.json / references/{brief,blogger-{catherine,couhuohuo},forbidden_words,output_schema.json} / scripts/{run_pipeline,risk_check,write_to_feishu}.py
- prompt 版本血缘:prompts/main_generation_v3_final.md(从 build_generation_prompt 提取)
- 触发评测桌面分析:docs/eval-trigger-analysis.md
- pytest 42 用例全绿

进行中 / 待办:
- 端到端真实跑(catherine + couhuohuo,需 ANTHROPIC_API_KEY 在 .env)
- 用独立 agent 评审 final_script 是否符合博主调性
- description 调优(参考 docs/eval-trigger-analysis.md)
- 飞书真实写入(需 FEISHU_* 凭证)

历史残留(等手动清):
- skills/mcn-script-assistant/mcn-script-assistant/ 嵌套目录(沙箱无法 rm)
- skills/.../scripts/schemas.py 与 references/output_schema.md 是上轮 Pydantic 路线的脚手架,Skill 已不依赖,可删
- feishu/write_to_feishu.py 与 skills/.../scripts/write_to_feishu.py 并存:前者是早期 batch_create + token cache 版本,后者是 Skill 内单条写入版本。两者职责略有差异,先并存。

---

## 你不知道的事(给你提个醒)

- 我已经用 Claude.ai 把 brief 拆解过了,结构化版本会放在 `references/brief.md`,你要写代码用到 brief 就读这个
- 博主已经选定 2 位,人工档案我会陆续放进 `references/blogger-*.md`。在那之前你写代码时假设档案存在即可,用 dummy fixture 做测试
- 飞书企业自建应用我已经创建好了,`app_id` 和 `app_secret` 在我本地 `.env`,你写代码引用环境变量名即可:`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_BITABLE_APP_TOKEN` / `FEISHU_BITABLE_TABLE_ID`
- 评审会拿到我的 GitHub 仓库链接和飞书表格分享链接。所以代码可以引用环境变量,但不能假设评审能跑通飞书写入——README 里要写清楚"如果你没有飞书 app 凭证,可以用 `--dry-run` 模式查看格式化后的输出"
