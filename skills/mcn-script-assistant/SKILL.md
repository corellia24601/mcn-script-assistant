---
name: mcn-script-assistant
description: 为 MCN 商单生成符合小红书平台规则的短视频脚本与分镜表。当用户提供品牌 brief、目标博主样本、投放平台时使用此 Skill,产出包含开头钩子、口播文案、产品植入点、结尾 CTA、6+ 镜头分镜、合规风险提醒的完整可拍摄脚本。务必在用户提到「小红书脚本」「商单」「种草脚本」「达人脚本」「分镜」「博主脚本」「投放脚本」或上传 brief 文档/博主资料时主动触发,即使用户未明确说「使用此 Skill」。该 Skill 强制执行广告法极限词检测、医疗承诺词拦截、品牌合规约束三层质检,并将最终产物写入飞书多维表格。
---

# MCN 小红书脚本助手

## 适用场景

本 Skill 用于以下三类典型场景:

1. **MCN 商单脚本交付**:客户提供品牌 brief 和已选博主,需要产出可拍摄的 60-90 秒短视频脚本 + 6+ 镜分镜表
2. **达人脚本风格化生成**:已有博主历史笔记拆解,需要按博主个人 IP 调性生成新脚本(而非通用商业文案)
3. **食品/快消品类合规脚本**:产品有强合规约束(如不能宣称减肥、降糖、治疗),需要在保留种草效果的同时通过广告法和小红书平台审核

**不适用场景**:
- 通用文案/微博/抖音脚本(平台调性不同)
- 直播带货脚本(交付物结构不同)
- 长视频(>3 分钟)脚本(本 Skill 优化的是短视频结构)

---

## 输入材料

调用本 Skill 前,必须确保 `references/` 目录下存在以下文件:

1. **品牌 brief**(必需):`references/brief.md`
   - 品牌名、产品、核心卖点、目标人群、投放平台、合规约束
   - 结构化 YAML 格式,详见 `references/brief.md` 模板

2. **博主风格档案**(必需,每位博主一个文件):`references/blogger-{id}.md`
   - 人设核心、视频结构、镜头语言、语言风格、产品植入路径
   - 没有档案则停止并要求用户提供

3. **违禁词库**(已内置):`references/forbidden_words.md`
   - 广告法极限词、医疗承诺词、平台违禁词、品类专属违禁词

**输入校验规则**:
- 缺失 brief.md → 中止,要求用户补充
- 缺失 blogger-*.md → 询问用户「请指定目标博主,或提供该博主的近期 2-3 条代表笔记内容」
- brief.md 中 `compliance_constraints.hard_red_lines` 缺失 → 警告并使用默认极限词库

---

## 执行步骤(共 6 步)

### Step 1 · Brief 拆解

读取 `references/brief.md`,产出结构化 JSON:

```json
{
  "brand": "...",
  "product": "...",
  "selling_points": [...],
  "audience": {
    "age": "...",
    "gender": "...",
    "interests": [...],
    "core_segments": [...]
  },
  "platform": "小红书",
  "total_script_duration_seconds": "60-90",
  "product_segment_duration_cap_seconds": 30,
  "non_ad_segments_duration_seconds": "30-60",
  "tone_constraints": "自然种草,不要硬广痕迹",
  "forbidden_terms": ["减肥", "瘦", "降糖", "最", "第一", "100%", ...],
  "forbidden_implications": [...],
  "soft_caution_zones": [...],
  "brand_differentiation": {
    "primary_asset": "...",
    "preferred_taglines": [...],
    "avoid_taglines": [...]
  }
}
```

### Step 2 · 博主风格档案加载

读取目标博主的 `references/blogger-{id}.md`,提取:

- **人设核心**:identity / emotional_tone / forbidden_persona_drift
- **视频结构模板**:几段式结构、各段时间比例
- **开场钩子模板**:开场镜头序列、首句配音模板、forbidden_openings
- **镜头语言**:shot_types_and_ratios、visual_effects
- **语言风格**:identifying_features 的 5 个维度 + 每个维度的 replication_rule
- **产品植入路径**:position、insertion_steps、duration_total
- **结尾风格**:pattern、forbidden_endings
- **合规风险提示**:compliance_specific_to_this_creator

**关键规则**:博主档案是**强约束**,生成脚本时不允许偏离。如果 brief 的诉求跟博主调性冲突(如 brief 要求精致,但博主是松弛搞笑型),以博主调性为准——因为脚本要让博主愿意拍、粉丝愿意看,而不是让品牌方满意。

### Step 3 · 脚本生成

按以下结构产出脚本(JSON 格式):

```json
{
  "title": "20 字内,带钩子,符合博主标题模板",
  "hook": {
    "duration_seconds": "0-5 秒",
    "shots": ["..."],
    "voiceover_first_line": "...",
    "bgm_note": "..."
  },
  "body": [
    {
      "timestamp": "5-15s",
      "segment_label": "...(对应博主视频结构的某一段)",
      "voiceover": "...",
      "shot_description": "..."
    }
  ],
  "product_insertion": {
    "at_second": "15-45s 区间",
    "transition_line": "我现在要 X",
    "package_close_up_duration": "2-3 秒",
    "sensory_description": "...(必须使用博主的 replication_rule,至少 1 个比喻 + 1 个具体感官词)",
    "action_shots": ["..."],
    "callback_at_ending": "...(如果博主档案要求结尾回扣)"
  },
  "cta": {
    "style": "...(必须符合博主结尾风格)",
    "voiceover": "..."
  },
  "compliance_notes": [
    "本脚本需要博主特别注意的措辞 #1",
    "本脚本需要博主特别注意的措辞 #2"
  ]
}
```

**生成时的强制规则**(违反任何一条都要重生成):

1. **交付定义**: 完整 60-90 秒脚本,由两类段落组成:
   - **核心交付段**(`segment_type: core_delivery`): 产品植入相关,博主必须按脚本拍,**总时长 ≤30 秒**
   - **参考方向段**(`segment_type: reference_only`): 模仿博主调性的非广内容,博主可调整,**总时长 30-60 秒**
2. **总时长**: 60-90 秒(项目硬性要求)
3. **植入时长上限**: 30 秒(MCN 业务硬约束,违反即拦截)
4. **非广段反照搬**: 不能直接复用博主原参考笔记的具体场景(如 Catherine 的「写脑爆材料/魔大食堂」、凑活活的「米露/挖野葱/星露谷」),必须从博主档案 `non_ad_content_palette` 取新场景
5. **品牌资产嵌入**: 可单独玩品牌名「轻醒」语义双关,但**禁止口播连读「品牌名+产品类目」全称**
6. **开场反硬广**: 标题、开场 10 秒、前 2 个分镜的口播和画面**不能指向产品**
7. **博主语言模板**: 必须命中博主档案 `language_style.identifying_features` 中至少 3 个特征
8. **感官描述**: 产品描述必须用具体感官词或比喻,禁用「真的好喝」「绝绝子」「YYDS」
9. **打工人黑话**(Catherine 限定): 必须有 1-2 处职场戏谑语言
10. **自嘲松弛**(凑活活限定): 必须有 1 处自嘲表达
11. **场景真实性**: 产品出现时博主已在产品的天然使用场景里

### Step 4 · 分镜拆解

基于脚本生成 ≥6 镜分镜表,每镜含:

| 字段 | 说明 |
|---|---|
| 镜头编号 | 1, 2, 3... |
| 时长(秒) | 1-15 秒 |
| 画面描述 | 主体 + 景别 + 动作 |
| 口播文案 / 字幕 | 对应口播片段或字幕文本框 |
| 道具与场景 | 拍摄需要准备的物品和场景 |
| 拍摄难度 | 低 / 中 / 高(便于博主排期) |

**镜头比例约束**(根据博主档案):

- Catherine: 前置自拍 ≥40%、第三视角中景 25%、画中画/特效 15%、工位特写 20%
- 凑活活: 第三视角 30%、第一视角主观 30%、手部特写 20%、产品近景 20%

### Step 5 · 风险质检

执行三层质检,任何一层命中即标记并要求修改:

#### 5.1 极限词扫描(`scripts/risk_check.py`)

读取 `references/forbidden_words.md`,扫描脚本所有文本字段:

```python
# 简要逻辑(实际见 scripts/risk_check.py)
forbidden = load_forbidden_words()
hits = []
for field in ["title", "hook.voiceover_first_line", "body[*].voiceover", "product_insertion.sensory_description", "cta.voiceover"]:
    for word in forbidden:
        if word in field_text:
            hits.append({"word": word, "field": field, "suggestion": get_replacement(word)})
```

#### 5.2 医疗/减肥承诺检测

LLM 自评:对脚本进行二次阅读,判断是否存在以下隐性违规:

- 暗示「吃了能瘦」(即使没用「瘦」字)
- 暗示「替代正餐控制热量」
- 暗示「比 X 食物更瘦/更低卡」
- 暗示「补充蛋白质」「增肌」等功能性宣称
- 「饱腹感」未配软化措辞(必须是「适合早上吃完比较扛饿」而非「吃了就不饿」)

#### 5.3 LLM-as-Judge 整体审查

让 LLM 以「小红书报备审核员」身份再读一次脚本,判断:

- 整体语境是否构成「暗示减肥/控糖/治疗」
- 是否存在 BMI 异常 / 极端身材叙事
- 博主语言是否真的像博主本人(风格相似度 1-10 分,低于 6 分重新生成)
- 是否给博主预留了 5-10% 自由发挥空间(避免完全 AI 化生硬感)

#### 5.4 输出质检报告 JSON

```json
{
  "compliance_status": "通过 / 警告 / 拦截",
  "extreme_words_hits": [...],
  "medical_implication_hits": [...],
  "llm_judge_score": {
    "overall_compliance": 8,
    "creator_style_similarity": 7,
    "naturalness": 8
  },
  "recommendations": [...]
}
```

**拦截阈值**:
- 极限词命中 ≥1 → 拦截
- 医疗承诺命中 ≥1 → 拦截
- LLM judge 任意维度 <6 → 警告(可继续但提示人工 review)
- LLM judge 任意维度 <4 → 拦截重生成

### Step 6 · 写入飞书多维表格

调用 `scripts/write_to_feishu.py`(或 Coze 工作流),写入字段:

| 字段名 | 类型 | 来源 |
|---|---|---|
| 脚本 ID | 文本 | 自动生成 (UUID) |
| 品牌 | 文本 | brief.brand |
| 目标博主 | 文本 | blogger.display_name |
| 生成时间 | 日期 | 当前时间 |
| 视频标题 | 文本 | 脚本 title |
| 开头钩子 | 多行文本 | 脚本 hook |
| 完整口播 | 多行文本 | 脚本 body 拼接 + product_insertion + cta |
| 分镜表 | 多行文本(JSON) | Step 4 输出 |
| 质检状态 | 单选 | Step 5 compliance_status |
| 质检详情 | 多行文本 | Step 5 完整 JSON |
| 备注 | 多行文本 | 人工备注栏 |

---

## 输出格式

最终输出 **3 份产物**:

1. **Markdown 文档**(`output/final_script.md`):人类可读版本,包含脚本 + 分镜表 + 合规提醒
2. **JSON 文件**(`output/final_script.json`):结构化版本,可被下游工具消费
3. **飞书多维表格记录**:实时同步到客户/评审可访问的飞书链接

---

## 风险检查清单(质检兜底)

- [ ] 没有「最/第一/独家/绝对/100%/唯一」等广告法极限词
- [ ] 没有「减肥/瘦身/减脂/燃脂/降糖/治疗/根治/疗效/抗衰老」等医疗承诺
- [ ] 没有违反广告法的功效绝对化表述
- [ ] **植入段落时长 ≤ min(博主常态笔记时长 × 25%, 30 秒)**(强约束,违反即拦截)
- [ ] **口播没有「轻醒酸奶」「轻醒希腊酸奶」类品牌+品类全称连读**(强约束)
- [ ] **标题不含「这勺/这一杯/这一罐」等指向产品的代词**(强约束)
- [ ] **开场 10 秒和前 2 个分镜的画面不出现产品近景特写或品牌字样清晰可见**(强约束)
- [ ] 标题 ≤20 字,符合小红书风格
- [ ] 所有产品功效描述都有「建议/帮助/适合」等软化措辞
- [ ] 给博主预留了「自由发挥段落」(笔记的开场、中段、结尾大部分内容由博主原创)
- [ ] 不与「BMI 异常」「极端瘦身」「催吐」等内容产生语境关联
- [ ] 「饱腹感」「高蛋白」「低负担」三个卖点均使用了软化措辞
- [ ] 品牌名「轻醒」的语义双关(轻 + 醒)在脚本中至少出现 1 次,但不与产品类目连读
- [ ] 博主语言风格匹配度 ≥6 分(LLM-as-Judge 评分)
- [ ] 产品出现位置符合博主档案中的 `product_insertion.position_in_full_note` 要求

---

## 兜底规则

1. **缺失博主档案** → 主动暂停并询问用户:「请指定目标博主,或提供该博主的近期 2-3 条代表笔记内容」
2. **质检命中 ≥3 条违规** → 自动重新生成而不是直接输出
3. **脚本生成超时或低质量** → 降级为「提供 3 个钩子方向 + 1 个分镜大纲」让用户人工补完
4. **博主调性跟 brief 强冲突** → 暂停并提醒用户:「该博主调性是 X,brief 诉求是 Y,建议要么换博主,要么调整 brief 的某些约束」(不强行融合)
5. **brief 临时变更**(如客户改了产品口味、加了直播投放、限制条款变化) → 重新执行 Step 1,而不是基于旧 brief 增量修改

---

## 边界场景处理

### 场景 1:客户改了产品口味
- 重新执行 Step 1,更新 `brief.md` 中的 `product.flavors`
- 在 Step 3 生成时强制使用新口味
- 老脚本归档不删除(放进 `output/archive/`)

### 场景 2:博主对脚本有微调诉求
- 不直接修改 SKILL.md,而是在 `references/blogger-{id}.md` 中添加 `creator_feedback` 字段
- 重新生成脚本,体现博主反馈

### 场景 3:同一品牌投放第二批博主
- 复用 `brief.md`(不变)
- 新增 `references/blogger-{new_id}.md`
- 在 Step 6 飞书表格中,新脚本会自动归到同一品牌名下,便于客户横向对比

### 场景 4:跨品类复用本 Skill(如不是酸奶,是低卡饼干)
- 替换 `references/brief.md` 全部内容
- 替换 `references/forbidden_words.md` 中的品类专属违禁词
- SKILL.md 主体不动,博主档案不动

---

## 设计原则

本 Skill 的设计遵循以下三条核心原则:

1. **博主调性 > 品牌诉求**:脚本要让博主愿意拍、粉丝愿意看,品牌植入是嵌入这两者的中间产物。如果硬把品牌诉求塞进博主不会说的话里,即使过审,也会被粉丝识别为广告而失去种草效果。

2. **合规优先 > 创意优先**:广告法和平台规则是硬约束,违反一次的代价(品牌负面公关 + 笔记被限流 + 法律责任)远超「这条创意被毙掉」的代价。所以质检环节是 3 层兜底,不是 1 层。

3. **结构化 > 散文化**:输入(brief、博主档案)、过程(6 步流程)、输出(JSON + 飞书)全部结构化。这不仅是工程上的好处,更是因为「**可被复盘的脚本生成过程才是真正可改进的过程**」——下次调优 Skill 时,知道哪一步出问题,而不是「整体感觉不对」。

---

## 版本与变更日志

```yaml
version: 1.0
created: 2026-04
last_updated: 2026-04
changes:
  - 1.0: 初始版本,支持「轻醒」希腊酸奶 × Catherine + 凑活活双博主组合
```

---

## 引用资源

- `references/brief.md` - 客户品牌 brief
- `references/blogger-catherine.md` - Catherine是小熊风格档案
- `references/blogger-couhuohuo.md` - 凑活活风格档案
- `references/forbidden_words.md` - 违禁词库
- `references/output_schema.json` - 输出 JSON Schema
- `scripts/risk_check.py` - 风险质检脚本
- `scripts/write_to_feishu.py` - 飞书多维表格写入脚本
