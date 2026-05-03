# main_generation prompt · v4 final

> 提取自 `skills/mcn-script-assistant/scripts/run_pipeline.py::build_generation_prompt`（v2 SKILL 升级版本）。
> 这是 Skill 当前实际投产用的脚本生成 prompt。v3 在 `main_generation_v3.md`，v4 是当前生效版本。

## 元数据

```yaml
version: v4-final
last_updated: 2026-05
calling_module: skills/mcn-script-assistant/scripts/run_pipeline.py::build_generation_prompt
called_by_step: SKILL.md Step 3 · 脚本生成
target_models:
  primary: claude-sonnet-4-6   # 通过 ANTHROPIC_MODEL_PRIMARY env 注入
  fallback: deepseek-chat      # Coze 工作流里成本更低的兜底
expected_output_format: JSON（不带 markdown 代码块标记）
expected_schema: skills/mcn-script-assistant/references/output_schema.json
```

## 占位符

| 占位符 | 来源 | 说明 |
|---|---|---|
| `{brief['raw_yaml_concatenated']}` | `references/brief.md` 中所有 ` ```yaml ` 块 | 客户 brief 完整结构化字段 |
| `{blogger_profile}` | `references/blogger-{id}.md` 原文 | 目标博主完整风格档案 |

## v3 → v4 关键演进

v4 引入 7 条「硬规则」放在 prompt 顶部，每条违反都触发重生成：

1. **植入时长 ≤30 秒**（业务硬约束）。总时长 60-90 秒，但植入段不能拉满。
2. **段落类型显式标记**：`body[i].segment_type = "core_delivery" | "reference_only"`。核心交付段是品牌方付费产出的部分，参考方向段是博主可自由替换的填充。
3. **非广段不能照搬博主原笔记的具体场景**。每位博主有 4 条「禁用场景」明列在 prompt 里（如 Catherine 的「写脑爆材料」「魔大食堂」、凑活活的「米露」「冷冻麻辣烫」）。下游用 `non_ad_content_palette`（博主档案新增字段）取材新场景。
4. **植入时长上限严格限制**。即使总时长拉到 90 秒，植入段也不能超过 30 秒，靠非广段补足。
5. **品牌名+品类不连读**。「轻醒酸奶」「轻醒希腊酸奶」禁用，要么单独说「叫轻醒」要么用替代指称（这罐子 / 这个）。
6. **标题 + 开场 10 秒 + 前 2 个分镜不指向产品**。挡掉硬广式开场（「这一勺」「这一杯」「i 人下班吃这个真的会上瘾」）。
7. **违禁词和功能性宣称硬禁止**（同 v3）。

## v4 新增的输出 schema 字段

```jsonc
{
  "duration_seconds": 75,
  "product_segment_duration_seconds": 25,        // ≤30，硬约束
  "non_ad_segments_duration_seconds": 50,
  "body": [
    {
      "segment_type": "reference_only" | "core_delivery",  // 新增
      "based_on_palette_item": "..."                       // 新增（非广段引用 palette）
    }
  ],
  "ending_callback": {                            // 新增（替代 v3 的 product_insertion.callback_at_ending）
    "applicable_to": "Catherine 必填 / 凑活活留空",
    "voiceover": "..."
  },
  "reasoning_check": {                            // 新增（自检字段）
    "title_avoids_product_pointer": "...",
    "opening_no_product": "...",
    "no_brand_full_name_in_voiceover": "...",
    "product_segment_within_30s": "...",
    "non_ad_segments_avoid_copying": "...",
    "total_duration_60_to_90": "..."
  }
}
```

`reasoning_check` 是自检字段——让模型自己回答 6 个二元问题，留痕给质检脚本看。risk_check.py 会把这个字段排除在违禁词扫描之外（避免「确认没有 X」式自检语句被误扫成命中）。

## prompt 全文（节选关键部分）

完整 prompt 见 `run_pipeline.py::build_generation_prompt`。这里只摘 v4 新增的 7 条硬规则原文：

````text
# ⚠️ 最重要的核心规则(违反任何一条都会被拦截重生成)

## 规则 1: 产出 60-90 秒完整脚本,其中植入段 ≤30 秒
**总时长**: 60-90 秒(项目硬性要求,不可少于 60 秒)
**产品植入段**: ≤30 秒(MCN 业务硬约束,目标 20-25 秒)
**非广内容段**: 30-60 秒(用模仿博主调性的内容补全)

## 规则 2: 脚本里的两类段落必须明确区分
- 核心交付段(产品植入相关): 博主必须按脚本拍,品牌方为这部分付费
- 参考方向段(非广内容补全): 博主可参考也可用她当下的生活素材替换

## 规则 3: 非广内容段必须避免照搬博主已有笔记
（Catherine / 凑活活 各 4 条禁用场景；从 non_ad_content_palette 取新场景）

## 规则 4: 严格控制植入时长
（不为了拉满总时长而拉长植入段）

## 规则 5: 口播台词不要连读「品牌名 + 产品类目」全称
❌ 「轻醒酸奶」「轻醒希腊酸奶」  
✅ 「这个酸奶」「叫轻醒」「黄桃口味的」

## 规则 6: 标题 + 开场 10 秒 + 前 2 个分镜不能指向产品
❌ 「打工人精神好的一天从这勺开始」  
✅ 「打工人精神好的秘诀(早起脑爆日)」

## 规则 7: 严禁违禁词和功能性宣称
（与 v3 一致：减肥/瘦/降糖/治疗/最/第一/100%/补充蛋白质/增肌/替代正餐/控住）
````

## 已知问题（待 v5 处理）

- prompt 长度从 v3 的 ~1.5K 字增加到 v4 的 ~3K 字。每次调用成本约翻倍（输入 tokens × 2）。规则 3 里的「博主禁用场景」每位博主硬编码进 prompt 里，加新博主要改 prompt——可以考虑改为从博主档案里读 `forbidden_specific_scenarios` 字段动态注入。
- 规则 6 的「前 2 个分镜不能指向产品」有歧义：分镜表是 derive_storyboard 派生的，prompt 写出的 `body` 段落不直接对应分镜。需要在 derive_storyboard 里也做检查，或者把规则改成「前 10 秒 body 段落不指向产品」。
- `reasoning_check` 是自检，不强校验——模型自己说「确认没有」不代表真没有。下一版可以让 risk_check.py 真的执行这 6 条二元检查。

## 变更记录

```yaml
v3-final 2026-04:
  - 提取自 build_generation_prompt（彼时单文档 prompt）
  - 已归档到 main_generation_v3.md

v4-final 2026-05:
  - 新增 7 条硬规则（植入时长 / 段落类型标注 / 非广段反复用 / 品牌名拆分 / 反开场硬广 / 标题反指向）
  - body schema 加 segment_type 区分核心交付 vs 参考方向
  - 输出加 reasoning_check 自检字段
  - product_insertion 字段被 ending_callback 替代
```
