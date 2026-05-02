# MCN Script Assistant Skill

> 为 MCN 商单生成符合小红书平台规则的短视频脚本与分镜表的 Claude Skill。
> 项目案例: 「轻醒」希腊酸奶 × Catherine是小熊 + 凑活活双博主组合。

---

## 项目结构

```
mcn-script-assistant/
├── SKILL.md                           # 主 Skill 文件,Claude 自动加载
├── eval-results.json                  # 20 条触发测试 query
├── README.md                          # (本文件)
├── references/                        # Skill 引用的资源
│   ├── brief.md                       # 客户 brief 结构化版本
│   ├── blogger-catherine.md           # Catherine 风格档案
│   ├── blogger-couhuohuo.md           # 凑活活风格档案
│   ├── forbidden_words.md             # 违禁词库
│   └── output_schema.json             # 输出 JSON Schema
└── scripts/                           # 执行脚本
    ├── risk_check.py                  # Step 5 质检脚本(独立可用)
    ├── write_to_feishu.py             # Step 6 飞书写入脚本
    └── run_pipeline.py                # 端到端 6 步流程
```

---

## 运行方式 1: 通过 Claude.ai / Cowork(推荐)

把整个 `mcn-script-assistant/` 目录放进 Claude 项目的 skills 目录,Claude 会自动读取 SKILL.md 并触发。

触发 query 示例:
- 「帮我写一个小红书脚本,推希腊酸奶,博主是 Catherine是小熊」
- 「按照凑活活的风格,生成一条 60 秒的种草脚本」
- (其他触发示例见 `eval-results.json`)

---

## 运行方式 2: Python 命令行端到端

适合需要本地调试或集成到其他工作流时。

### 安装依赖

```bash
pip install anthropic requests
```

### 配置环境变量

```bash
# 必需(用于 Step 3 调用 Claude 生成脚本)
export ANTHROPIC_API_KEY="sk-ant-..."

# 可选(用于 Step 6 写入飞书,不配置会自动跳过)
export FEISHU_APP_ID="cli_..."
export FEISHU_APP_SECRET="..."
export FEISHU_BITABLE_APP_TOKEN="..."   # 多维表格 URL 中的 app_token
export FEISHU_BITABLE_TABLE_ID="tbl..."  # 多维表格 URL 中的 table_id
```

### 运行

```bash
# 为 Catherine 生成脚本
cd mcn-script-assistant
python scripts/run_pipeline.py --blogger catherine_xiaoxiong

# 为凑活活生成脚本(不写入飞书)
python scripts/run_pipeline.py --blogger couhuohuo --no-feishu

# 质检失败时最多重生成 2 次
python scripts/run_pipeline.py --blogger catherine_xiaoxiong --regenerate-on-fail 2
```

输出文件:
- `output/final_script_{blogger_id}.json` - 结构化脚本
- `output/final_script_{blogger_id}.md` - 人类可读 Markdown 版

---

## 运行方式 3: Coze 工作流

`run_pipeline.py` 的逻辑可以拆解到 Coze 节点中:

| Coze 节点 | 对应 Step |
|---|---|
| 开始节点(输入 brief + 博主名) | - |
| 文件读取节点 | Step 1 + 2(读 brief.md + blogger-{id}.md) |
| LLM 节点(调用 Claude/DeepSeek/豆包) | Step 3(脚本生成) |
| 代码节点(运行 derive_storyboard) | Step 4(分镜派生) |
| 代码节点(调用 risk_check.check_script) | Step 5(质检) |
| 飞书多维表格插件(add_records) | Step 6(写入) |
| 结束节点(返回飞书链接 + 脚本 JSON) | - |

**优势**: Coze 的飞书插件比直接调 API 简单一个数量级,授权也更方便。
**劣势**: 需要在 Coze 里手动搭建,无法直接复用本仓库的 Python 代码,但 prompt 和质检规则可以直接复制过去。

---

## 单独使用各个脚本

### 仅运行质检

```bash
python scripts/risk_check.py \
    --script output/some_script.json \
    --output output/compliance_report.json

# 启用 LLM-as-Judge(更严格)
python scripts/risk_check.py \
    --script output/some_script.json \
    --blogger-profile references/blogger-catherine.md \
    --llm-judge
```

退出码:
- `0` = 通过
- `1` = 警告
- `2` = 拦截

### 仅写入飞书

```bash
# Dry run(只格式化不写入)
python scripts/write_to_feishu.py \
    --script output/some_script.json \
    --dry-run

# 实际写入
python scripts/write_to_feishu.py --script output/some_script.json
```

---

## 切换到其他品牌/博主

本 Skill 设计为可复用,切换品牌或博主时:

### 切换品牌
1. 替换 `references/brief.md` 全部内容
2. 在 `references/forbidden_words.md` 中更新「品牌专属约束」一节
3. SKILL.md / 博主档案 / 其他脚本不动

### 添加新博主
1. 新建 `references/blogger-{new_id}.md`(参考现有两份的结构)
2. 在 `scripts/run_pipeline.py` 的 `_get_display_name` 中添加映射
3. SKILL.md 不动

### 切换品类(如不是酸奶,是低卡饼干)
1. 替换 `references/brief.md`
2. 替换 `references/forbidden_words.md` 中的「品类专属违禁词」
3. SKILL.md 主体不动,博主档案不动

---

## 设计原则

1. **博主调性 > 品牌诉求**: 脚本要让博主愿意拍、粉丝愿意看,品牌植入是嵌入这两者的中间产物
2. **合规优先 > 创意优先**: 广告法和平台规则是硬约束,质检是 3 层兜底
3. **结构化 > 散文化**: 输入(brief、博主档案)、过程(6 步流程)、输出(JSON + 飞书)全部结构化

---

## 已知限制与待办

- [ ] LLM-as-Judge 默认未启用(避免双倍 API 调用)。生产环境建议开启。
- [ ] 风险质检的隐性违规检测目前是基于正则的规则引擎,覆盖度有限。完整解决方案需要 LLM 二次审查。
- [ ] 飞书多维表格的字段名需要在飞书后台手动创建匹配,本脚本不会自动建表。
- [ ] 当前 Skill 只支持 60-90 秒短视频,长视频/直播脚本需要扩展。
- [ ] eval-results.json 是设计的测试 query 集合,实际触发结果需要用户手动跑一遍验证。

---

## 测试 Skill 触发准确性

```bash
# 把 eval-results.json 中的 should_trigger 一条条粘贴到 Claude.ai
# 验证每条都能正确加载本 Skill
# 目标: should_trigger ≥ 10/12, should_not_trigger ≥ 7/8
```

---

## 版本

- v1.0 (2026-04): 初始版本,支持「轻醒」希腊酸奶 × Catherine + 凑活活
