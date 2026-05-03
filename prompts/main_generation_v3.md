# main_generation prompt · v3

> 提取自 `skills/mcn-script-assistant/scripts/run_pipeline.py::build_generation_prompt`。
> 这不是当前prompt版本。Skill 当前实际投产用的脚本生成 prompt 是（v4），保留v3是为了和后续版本（v4、v5……）做 diff 对比，建立 prompt 版本血缘。

## 元数据

```yaml
version: v3-final
last_updated: 2026-04
calling_module: skills/mcn-script-assistant/scripts/run_pipeline.py::build_generation_prompt
called_by_step: SKILL.md Step 3 · 脚本生成
target_models:
  primary: claude-opus-4-7   # 调用代码里写死的；CLAUDE.md 要求 .env 注入，待重构
  fallback: deepseek-chat    # Coze 工作流里成本更低的兜底
expected_output_format: JSON（不带 markdown 代码块标记）
expected_schema: skills/mcn-script-assistant/references/output_schema.json
```

## 占位符

构造时通过 Python f-string 注入两段动态内容：

| 占位符 | 来源 | 说明 |
|---|---|---|
| `{brief['raw_yaml_concatenated']}` | `references/brief.md` 中所有 ` ```yaml ` 块拼接 | 客户 brief 的全部结构化字段 |
| `{blogger_profile}` | `references/blogger-{id}.md` 原文 | 目标博主完整风格档案 |

## prompt 全文

````text
你是一位资深的 MCN 内容策划,专门为小红书品牌商单撰写短视频脚本。

# 客户 Brief(结构化 YAML)

```yaml
{brief['raw_yaml_concatenated']}
```

# 目标博主风格档案

{blogger_profile}

# 任务

请为该博主生成一条 60-90 秒的小红书短视频脚本。**严格遵循以下规则**:

## 强制规则

1. **博主调性 > 品牌诉求**:必须保留博主原本的语言习惯、镜头偏好、视频结构
2. **博主语言模板**:必须命中博主档案 `language_style.identifying_features` 中至少 3 个特征
3. **感官描述**:产品描述必须用具体感官词或比喻,**禁用「真的好喝」「绝绝子」「YYDS」**
4. **场景真实性**:产品出现时博主已在产品天然使用场景里,不能「突然切到产品镜头」,必须先有「我现在要 X」过渡句
5. **品牌资产嵌入**:脚本中必须自然出现品牌名「轻醒」的语义双关(轻 + 醒)
6. **合规约束**:严禁使用减肥、瘦身、降糖、治疗、最、第一、100% 等违禁词,严禁暗示减肥/降糖/治疗效果

## 输出格式

请只返回符合以下结构的 JSON,不要任何其他文字或代码块标记:

```json
{
  "title": "20 字内,带钩子,符合博主标题模板",
  "duration_seconds": 75,
  "hook": {
    "duration_seconds": "0-5 秒",
    "shots": ["镜头1描述", "镜头2描述", "镜头3描述", "镜头4描述", "镜头5描述"],
    "voiceover_first_line": "首句配音",
    "bgm_note": "BGM 描述"
  },
  "body": [
    {
      "timestamp": "5-15s",
      "segment_label": "起床段 / 当下美食段 / 等",
      "voiceover": "口播文案",
      "shot_description": "画面描述"
    }
  ],
  "product_insertion": {
    "at_second": "15-45s 区间",
    "transition_line": "我现在要 X",
    "package_close_up_duration": "2-3 秒",
    "sensory_description": "至少 1 个比喻 + 1 个具体感官词",
    "action_shots": ["动作镜头1", "动作镜头2"],
    "callback_at_ending": "结尾回扣的口播(Catherine 必填,凑活活可选)"
  },
  "cta": {
    "style": "留白式 / 戏剧化感受式 / 自嘲总结式 / 回扣式",
    "voiceover": "结尾口播"
  },
  "compliance_notes": [
    "本脚本拍摄时博主需要注意的措辞 1",
    "本脚本拍摄时博主需要注意的措辞 2"
  ]
}
```

只返回 JSON,不要 markdown 代码块标记,不要解释。
````

## 设计取舍（v3 vs 早期假设版本 v1/v2）

虽然本仓库没有保留 v1/v2 的 markdown，但 v3 相对早期方案的演进点有：

1. **从单文档喂入 → 双文档嵌入**：v1 只塞 brief，让模型自由发挥；v2 加了博主档案的少量摘要；v3 直接把博主档案原文整段嵌入，因为博主调性是核心约束，不能损失上下文。
2. **强制规则从 3 条加到 6 条**：v1/v2 没有显式的「博主调性 > 品牌诉求」「场景真实性」两条。在评审中观察到模型常见失败模式是：把博主调性稀释成通用商业文案、产品出现得突兀。这两条作为硬约束写进 prompt 后召回率明显提高。
3. **输出格式从 markdown → JSON**：v1/v2 让模型直接出 markdown，发现下游飞书/质检脚本解析困难。v3 转成 JSON 并显式约束 schema，配合 `references/output_schema.json` 校验。
4. **callback_at_ending 区分两位博主**：v3 在 schema 里给 `callback_at_ending` 字段标注「Catherine 必填,凑活活可选」，对应博主档案里的 signature_structure 差异。

## 已知问题（待 v4 处理）

- 模型名 `claude-opus-4-7` 写死在调用代码 `call_claude_for_script` 里，没从 `.env` 注入。CLAUDE.md 明确要求所有模型名通过 env 传入，下版本要修。
- prompt 里 `forbidden_terms` 没有显式列举，依赖模型自己理解「合规约束」。生产环境建议在 prompt 末尾追加一段「以下词不得使用」清单（从 `references/forbidden_words.md` 派生）。
- 没有显式 few-shot 示例。当前完全依赖博主档案里的 examples 做隐性 few-shot。如果某些博主档案 examples 偏少，生成质量会受影响。

## 变更记录

```yaml
v3-final 2026-04:
  - 提取自 run_pipeline.py，独立托管以建立版本血缘
  - 已知问题与 v4 演进方向标注在「设计取舍 / 已知问题」两节
```
