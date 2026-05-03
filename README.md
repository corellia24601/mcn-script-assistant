# mcn-script-assistant

MCN 商单短视频脚本自动化生成的 Skill，配套 Coze 工作流、飞书多维表格写入脚本和质检流水线。使用Claude Code辅助搭建。

> **当前进度**：Skill 主体（`skills/mcn-script-assistant/`）已落位、端到端 pipeline 跑通；prompt 版本血缘已建（`prompts/main_generation_v3_final.md`）；触发评测桌面分析已写（`docs/eval-trigger-analysis.md`）。

## 业务场景

- **客户 brief**：轻醒酸奶 · 0 蔗糖高蛋白希腊酸奶
- **目标人群**：22–35 城市女性
- **平台**：小红书短视频
- **要求**：自然种草；不得承诺减肥 / 降糖 / 治疗

完整 brief 拆解见 `skills/mcn-script-assistant/references/brief.md`，博主选型见 `references/blogger-{catherine,couhuohuo}.md`。

## 仓库结构

```
.
├── skills/mcn-script-assistant/      # Anthropic Skills 标准目录（canonical 交付物）
│   ├── SKILL.md                      # description 触发 + 6 步执行流程
│   ├── eval-results.json             # 12+8 触发评测 query
│   ├── README.md                     # Skill 内部 README（Claude.ai/Cowork/CLI/Coze 三种用法）
│   ├── report.md                     # 调研与方案报告
│   ├── references/
│   │   ├── brief.md                  # 客户 brief 结构化版本
│   │   ├── blogger-catherine.md      # Catherine 风格档案
│   │   ├── blogger-couhuohuo.md      # 凑活活风格档案
│   │   ├── profile_catherine.png     # Catherine小红书主页截图
│   │   ├── profile_couhuohuo.png     # 凑活活小红书主页截图
│   │   ├── ref_video_catherine.png   # Catherine参考视频截图
│   │   ├── ref_video_couhuohuo.png   # 凑活活参考视频截图
│   │   ├── sample_video_decode.md    # Catherine+凑活活的参考视频拆解（含链接）
│   │   ├── forbidden_words.md        # 违禁词库
│   │   ├── output_schema.json        # 输出 JSON Schema（canonical）
│   │   ├── output_schema.md          # 上一轮的脚手架，已被 .json 取代
│   │   ├── forbidden_words.md        # 违禁词库
│   │   ├── output_schema.json        # 输出 JSON Schema（canonical）
│   │   ├── output_schema.md          # 上一轮的脚手架，已被 .json 取代
│   │   └── blogger-template.md       # 通用博主档案模板
│   └── scripts/
│       ├── run_pipeline.py           # 端到端 6 步 pipeline
│       ├── risk_check.py             # Step 5 三层质检（极限词 + 隐性 + LLM-as-Judge）
│       ├── write_to_feishu.py        # Step 6 飞书 bitable 写入
│       └── schemas.py                # 上一轮的 Pydantic 脚手架，已不被 Skill 使用
├── prompts/
│   └── main_generation_v3_final.md   # 从 build_generation_prompt 提取的 v3 prompt
├── feishu/
│   └── write_to_feishu.py            # 早期可独立使用的飞书 batch_create 模块（与 Skill 内版本并存）
├── coze/code_nodes/
│   └── format_converter.py           # Coze 代码节点：脚本 → 表格 records
├── tests/                            # pytest 单测（42 用例）
├── docs/
│   ├── workflow.mermaid              # 端到端工作流图
│   └── eval-trigger-analysis.md      # description 触发桌面分析
├── output/                           # run_pipeline.py 生成产物（gitignored 之外的，进 git）。包含最终输出脚本
├── .env.example
├── pyproject.toml
└── CLAUDE.md
```

> **结构残留说明**：`skills/mcn-script-assistant/mcn-script-assistant/` 是上一轮初始化时不小心多套的一层，里面文件已平铺到外层，等 Windows 下手动 `rm -rf` 清掉即可。

### 关于两个 references/ 目录

仓库里有两个同名目录，承担不同职责：

- **`references/`**（仓库根）：原始调研材料——博主笔记截图、URL 列表、人工拆解笔记
- **`skills/mcn-script-assistant/references/`**：Skill 内部配置——结构化 brief、博主档案、违禁词库、output schema

调研材料是**形式化前**的原始素材，Skill 配置是**形式化后**的程序消费物。前者支撑 `report.md` 的判断逻辑，后者驱动 `run_pipeline.py` 的执行。

## 快速开始

### 1. 准备环境

```bash
uv sync
cp .env.example .env
# 在 .env 填 ANTHROPIC_API_KEY、可选填飞书凭证
```

### 2. 跑测试

```bash
uv run pytest
# 应看到 42 passed
```

### 3. 端到端跑 pipeline

```bash
# 默认 dry-run 飞书（无飞书凭证也能跑）
uv run python skills/mcn-script-assistant/scripts/run_pipeline.py --blogger catherine_xiaoxiong --no-feishu
uv run python skills/mcn-script-assistant/scripts/run_pipeline.py --blogger couhuohuo --no-feishu

# 输出：output/final_script_{blogger_id}.{json,md}
```

### 4. 单独跑质检

```bash
uv run python skills/mcn-script-assistant/scripts/risk_check.py \
    --script output/final_script_catherine_xiaoxiong.json \
    --output output/compliance_report.json

# 退出码 0=通过 / 1=警告 / 2=拦截
```

### 5. 单独跑飞书写入

```bash
# Dry-run，只打印 fields
uv run python skills/mcn-script-assistant/scripts/write_to_feishu.py \
    --script output/final_script_catherine_xiaoxiong.json --dry-run

# 实际写入（需 FEISHU_* 凭证）
uv run python skills/mcn-script-assistant/scripts/write_to_feishu.py \
    --script output/final_script_catherine_xiaoxiong.json
```

或者用 `feishu/write_to_feishu.py`（早期版本，支持 batch_create + 内存 token cache）：

```bash
uv run python -m feishu.write_to_feishu records.json --commit
```

## 工作流概览

端到端流程见 `docs/workflow.mermaid`。简述：

1. brief 与博主档案手工整理 → `skills/.../references/`
2. `run_pipeline.py` 读取 brief + 博主档案，调用 Claude 生成脚本 JSON（Step 1-3）
3. 派生分镜表（Step 4）
4. `risk_check.py` 三层质检（Step 5）：极限词 + 隐性违规 + 可选 LLM-as-Judge
5. 命中 H 级或拦截 → 自动重生成（最多 N 次）
6. `write_to_feishu.py` 写入飞书多维表格（Step 6，可选）
7. 评审通过共享链接查看结果

## Coze 工作流映射

`run_pipeline.py` 是「Coze 工作流的兜底实现 + 逻辑参考」。Coze 节点对应关系：

| Coze 节点 | 对应 Step | 复用 |
|---|---|---|
| 文件读取 | Step 1+2 | brief.md / blogger-*.md |
| LLM 节点 | Step 3 | prompt 来自 `prompts/main_generation_v3_final.md` |
| 代码节点 | Step 4 | 复用 `coze/code_nodes/format_converter.py` 类似逻辑 |
| 代码节点 | Step 5 | 直接 import `risk_check.check_script` |
| 飞书插件 add_records | Step 6 | 比直接调 API 简单 |

## 设计取舍

- **没有用 langchain/openai sdk**。模型调用直接 `requests` 或官方 `anthropic`，避免拖一堆抽象。
- **forbidden_words.md 是单一数据源**。脚本启动时解析，不维护额外 JSON。
- **飞书写入默认 dry-run**（`feishu/`版本）或显式凭证缺失时跳过（`skills/.../scripts/`版本）。
- **三层质检兜底**：关键词扫描 + 隐性正则 + 可选 LLM-as-Judge。前两层无 API 成本，LLM 层在重要场景启用。
- **prompt 版本血缘**：每次大改 prompt 就在 `prompts/main_generation_vN.md` 落版本，diff 看演进。

## 安全红线

- `.env` 已 `.gitignore`，仓库内不出现真实凭证
- 不写小红书爬虫；博主数据由人工提供
- 不调用任何"修改文档权限"接口；评审用的飞书表格分享由仓库主人手工生成

详见 `CLAUDE.md`。

## 测试与提交

```bash
uv run pytest      # 42 passed
git add ...
git commit -m "feat: ..."   # Conventional Commits
# 不在 CI 之外手动 push；由仓库主人统一 push
```

## License

仅作为实习笔试交付。
