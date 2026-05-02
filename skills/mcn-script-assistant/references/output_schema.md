# 脚本输出 JSON Schema

> Skill 生成的每条短视频脚本必须满足下面这套 schema。Coze 工作流的代码节点和飞书写入脚本都依赖它。
> 实际 Pydantic 类定义在 `skills/mcn-script-assistant/scripts/schemas.py`。

## 顶层结构

```jsonc
{
  "blogger_id": "string",            // 关联 references/blogger-*.md 里的 id
  "script_id": "string",             // 由生成端给出，e.g. "qx-2026Q2-01"
  "platform": "xiaohongshu",         // 当前固定值
  "video_length_sec": 60,            // 整数，建议 30-90
  "hook": { "..." },                 // 见下
  "scenes": [ { "..." } ],           // 3-6 个场景
  "cta": "string",                   // 行动召唤
  "tags": ["string"],                // 5-10 个 hashtag，不带 #
  "risk_flags": [ { "..." } ],       // 质检脚本回填
  "meta": { "..." }                  // 模型/版本等可选 trace
}
```

## hook（开头 3 秒钩子）

```jsonc
{
  "text": "string",         // 钩子文案，<= 30 字
  "visual": "string",       // 一句话画面提示
  "type": "pain_point | scene | question | counterintuitive"
}
```

## scenes[i]

```jsonc
{
  "order": 1,
  "duration_sec": 8,
  "scene": "string",        // 画面描述，<= 80 字
  "voiceover": "string",    // 旁白/配音文案，<= 100 字
  "on_screen_text": "string"  // 字幕，<= 30 字，可空串
}
```

## risk_flags[i]（由 risk_check.py 回填）

```jsonc
{
  "level": "H | M | L",
  "matched": "string",      // 命中的词或 regex 结果
  "location": "hook | scenes[2].voiceover | cta | tags[3] | ...",
  "rule": "string",         // forbidden_words.md 里的类别
  "suggestion": "string"    // 建议改写的方向（不必给出最终改写）
}
```

## meta

```jsonc
{
  "model": "deepseek-chat",
  "skill_version": "0.1.0",
  "generated_at": "2026-04-30T12:00:00Z",
  "brief_version": "qx-2026Q2"
}
```

## 字段约束（用 Pydantic 落地）

- `video_length_sec` ∈ [30, 90]
- `scenes` 数量 3-6，且 `sum(duration_sec) ≈ video_length_sec ± 5`
- `tags` 不能包含 `#`、不能含违禁词
- 任何字段命中 H 级违禁词时，整条脚本必须 `risk_flags` 非空且包含 H 级条目，否则视作生成失败

## 输出示例

只演示结构，不代表真实文案。

```json
{
  "blogger_id": "xx-001",
  "script_id": "qx-2026Q2-01",
  "platform": "xiaohongshu",
  "video_length_sec": 60,
  "hook": {
    "text": "下午三点又开始馋甜的？",
    "visual": "办公桌上摊开的零食袋",
    "type": "scene"
  },
  "scenes": [
    {
      "order": 1,
      "duration_sec": 10,
      "scene": "镜头特写打开希腊酸奶杯",
      "voiceover": "我最近嘴馋的时候会先翻冰箱",
      "on_screen_text": "下午茶替代清单"
    }
  ],
  "cta": "评论区聊聊你的下午茶替代搭配",
  "tags": ["希腊酸奶", "下午茶搭配", "高蛋白早餐"],
  "risk_flags": [],
  "meta": {
    "model": "deepseek-chat",
    "skill_version": "0.1.0",
    "generated_at": "2026-04-30T12:00:00Z",
    "brief_version": "qx-2026Q2"
  }
}
```
