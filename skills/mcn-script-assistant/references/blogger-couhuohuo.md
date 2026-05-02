# 博主风格档案 · @凑活活

> 本档案用于 SKILL.md 中的 Step 2「博主风格档案加载」环节。它的目的不是描述博主,而是让脚本生成 LLM 能模仿出博主调性。

---

## 一、基础信息

```yaml
profile:
  id: couhuohuo
  display_name: 凑活活
  platform: 小红书
  fans: 251500
  fan_demographics:
    female_ratio: 98.6%
    age_18_24: 54.5%
    age_25_34: 27.3%
  active_hours: 凌晨 12-1 点(高度集中)
  
content_role: 数据保底 + 场景互补
matching_strategy: |
  「宅女+梗多笑点多」表层与 brief 错位,但内容深处有「上班前一小时记录」+「自己做饭」承接早餐场景。
  人设是「松弛中带自我管理」,跟 Catherine 形成「松弛日常 vs 紧凑工位」的互补叙事。
```

## 二、人设核心(脚本生成时必须保留)

```yaml
persona_core:
  identity: 都市独居宅女,有自己的小日常和小手作
  emotional_tone: 松弛 / 自嘲 / 不紧绷 / 计划赶不上变化也没事
  not_about:
    - 不是「自律博主」
    - 不是「精致生活方式博主」
    - 不是「正能量打工人」
  about:
    - 是「过日子的女生,日子里有小坚持」
    - 「装大象一样,一共就 3 步」式的化繁为简

forbidden_persona_drift:
  # 这些方向会破坏她的人设,脚本绝对不能往这些方向写
  - 不要把她写成「健身博主」
  - 不要让她讲「自律」「卷」「努力」
  - 不要让她说「家人们」「OMG」「绝绝子」「冲冲冲」
  - 不要让她做「测评/对比/盘点」类内容
```

## 三、视频结构模板(长 vlog 5 段式)

```yaml
# 博主常态笔记时长
typical_note_duration:
  range: 6-8 分钟(360-480 秒)
  reference_note_duration: 8 分 37 秒(《老乡,人生可以是星露谷》)
  product_segment_duration_in_reference: 约 20 秒(家乐麻酱拌面汁植入,占完整笔记 3.9%)

# 商单脚本交付定义(重要)
deliverable_definition:
  total_script_duration: 60-90 秒(项目硬性要求)
  product_segment_duration: ≤30 秒(MCN 业务最佳实践)
  non_ad_segments_duration: 30-60 秒(用补全的博主调性内容填充)
  
  what_blogger_must_film: 产品植入段(脚本中标注「核心交付」的部分)
  what_blogger_can_adjust: 非广内容段(脚本中标注「参考方向」的部分,博主可按当下生活素材调整)
  total_blogger_note_length: |
    博主可以选择按 60-90 秒交付完整笔记,
    也可以把脚本中的植入段嵌入到她常态 6-8 分钟笔记里。
    无论哪种,植入段时长不变(≤30 秒)。

# 非广内容素材池(用于补全段,避免照搬原笔记)
non_ad_content_palette:
  # 这些是凑活活常态会拍但参考笔记《老乡,人生可以是星露谷》里没出现过的场景类型
  # 写补全段时从这里取材,而不是抄「米露/麻辣烫/挖野葱/水晶手串」
  
  small_daily_incidents:
    # 类似「平安夜把床弄脏」的小日常意外/起点
    - 早上发现昨晚的快递忘了拆,堆在门口三天
    - 想找一双袜子但只能找到 1 只
    - 喝水的杯子被自己不小心碰倒了,水洒了半桌
    - 早上开冰箱发现昨天剩的菜还没吃
    - 睡到自然醒发现已经 11 点
    - 收到一个不知道是谁寄的包裹
    - 阳台的多肉今天好像有点蔫
  
  food_scenarios:
    # 类似「米露/麻辣烫」的在家做食物场景
    - 煮一锅速冻饺子,加一个荷包蛋
    - 拿一片吐司涂果酱配豆浆
    - 中午懒得做饭,煮个泡面但加了三个菜
    - 烤箱热一块隔夜披萨
    - 切一个苹果,做一个简单的水果碗(产品可在这里自然出现)
    - 自己冲一杯咖啡 / 茶,守着窗台喝
  
  domestic_actions:
    # 类似「整理床单」「制作手串」的居家小事
    - 整理书架,把书按颜色重新排
    - 给绿植换盆 / 浇水 / 修叶子
    - 把家里所有的便签条都揭下来重写
    - 整理抽屉,发现一些忘了存在的东西
    - 拆一个新买的小物件,跟它合影
    - 自己给自己剪刘海(剪坏了也没事)
  
  outdoor_micro_adventures:
    # 类似「挖野葱」的小型户外活动(可选,不一定必须有)
    - 去家附近便利店买一瓶饮料
    - 楼下散步,拍几只猫
    - 在小区里给小区流浪猫拍照
    - 突然下雨在屋檐下躲雨
    - 去快递柜取快递,顺路买根冰棍
  
  # 凑活活的标志性叙事节奏
  narrative_rhythm:
    - 「计划落空 → 凑合一下也挺好」是她最常用的反转结构
    - 「装大象一样,3 步」式的化繁为简(可作为风格参考,但不要直接套用相同句式)
    - 自嘲收尾:「最后还是 X」「其实也没怎么样」式的留白

# 完整笔记的内容结构(供博主理解,我们不写)
full_length_5_segments:
  - segment: 意外起点
    time_ratio: 0-5% of full note
    content: 快闪 + 一个小日常意外/小麻烦
    example: 「昨晚是平安夜,偏偏早上起床的时候把床弄脏了」
  
  - segment: 当下美食
    time_ratio: 5-30% of full note
    content: 聚焦一两样具体的吃喝,完整制作过程 + 第一口反应
    key_role: 这是产品植入的黄金位置(植入段落嵌入这里)
  
  - segment: 计划行动
    time_ratio: 30-60% of full note
    content: 换装出门做一件「有仪式感但不重要」的事
  
  - segment: 落空反转
    time_ratio: 60-80% of full note
    content: 事情没按计划成功,用幽默和自嘲消化失败感
  
  - segment: 治愈收尾
    time_ratio: 80-100% of full note
    content: 回家做点东西转化「失败」+ 留白结束
```

## 四、开场钩子模板

```yaml
opening_hook:
  pattern: 3-6 个生活片段快闪 + 一句配音「定情绪」
  
  shots_in_first_5_seconds:
    - 第三视角中景: 博主在做今天会发生的事之一
    - 第一视角主观: 拍今天会用到的物品
    - 第三视角细节: 展示一个手作/物品成果
    - 中景动作: 切菜/下面/整理
  
  first_voiceover_template:
    structure: 时间锚点 + 具体小事 + 共情语
    examples:
      - 「昨晚是平安夜,偏偏早上起床的时候把床弄脏了」
      - 「今天周一,但我居然 7 点就醒了,这种事一年发生不了几次」
      - 「最近这个天气吧,在家待着不动又有点冷」
  
  forbidden_openings:
    - 「家人们,今天给大家分享一款好物」
    - 「OMG 你们一定要看完」
    - 「不允许还有人不知道...」
    - 任何带「冲」「快」「绝」的快节奏感叹
```

## 五、镜头语言

```yaml
camera_language:
  shot_types_and_ratios:
    third_person_medium:
      ratio: 30%
      use_for: 「介绍今天要做什么」「展示穿搭」「全身入境的动作」
    
    first_person_subjective:
      ratio: 30%
      use_for: 拍手中物品、做饭过程、近距离细节
    
    hand_close_up:
      ratio: 20%
      use_for: 揉米露/拌菜/挖一勺等动作,持续 1-3 秒就切
    
    product_close_up:
      ratio: 20%
      use_for: 产品包装、成品摆盘,常配「文本框 + 产品名」字幕
  
  rule: |
    任何一种镜头持续超过 5 秒就要切。
    每条 60-90 秒脚本至少包含这 4 类镜头各 1-2 个,不要全是单一视角。
  
  visual_effects:
    use:
      - BGM(抖音热曲,3-5 秒切走)
      - 文本框字幕(产品名、玩梗别名)
    avoid:
      - 脸部变形滤镜(凑活活很少用)
      - 电子配音(凑活活很少用)
```

## 六、语言风格(核心识别特征)

```yaml
language_style:
  identifying_features:
    
    # 特征 1: 玩梗式品牌别名
    pun_branding:
      description: 不直接说品牌名,用谐音/调侃版本
      examples:
        - 「并非拉夫劳伦,是宝宝散步」(指保罗)
        - 「老演员冷冻麻辣烫」
      replication_rule: |
        产品名第一次出现时带一个调侃别名,后续才正名。
        比如「轻醒」可以叫「轻轻醒醒小酸奶」「轻醒老乡」。
    
    # 特征 2: 博主圈互文
    creator_reference:
      description: 自然提到其他博主的外号,营造「我们一起看小红书」的社群感
      example: 「这让我想起一位博主,瘦干螂」
      replication_rule: 适度使用,1 条脚本最多 1 处。
    
    # 特征 3: 流行语 + 网络热曲
    trending_bgm:
      description: 抖音热曲随情节切入,3-5 秒就切走
      examples:
        - 「搓搓~搓搓~」(揉东西时)
        - 「我们不是情侣,却要黏在一起」(配捣米)
    
    # 特征 4: 具体感官描述
    sensory_specificity:
      description: 从不说「好吃」「好喝」,只用能让人脑补出味道的具体词
      examples:
        - 「带一点淡淡的麦芽香」
        - 「软软糯糯的大米」
        - 「放进冰箱冷藏很好喝」
      replication_rule: |
        描述「轻醒」希腊酸奶必须用具体感官词:
        - 「挖一勺立起来不滴」
        - 「酸度比 X 柔但奶味更厚」
        - 「黄桃丁咬到的瞬间像周二突然变成周五」
        禁用:「真的太好喝了」「绝绝子」「YYDS」
    
    # 特征 5: 自嘲 + 松弛
    self_deprecating:
      description: 降低观众心理防线,让产品出现时不像广告
      examples:
        - 「计划赶不上变化」
        - 「跟装大象一样,一共就 3 步」
        - 「多么痛的领悟,只有女生能懂」
      replication_rule: 每条脚本至少 1 处自嘲。
```

## 七、产品植入路径(本博主的标准模板)

```yaml
product_insertion:
  position: 当下美食段尾部(60-90 秒脚本的 30-65 秒区间)
  
  insertion_steps:
    step_1: 博主已经在做相关场景的事
      example: 在煮麻辣烫 / 准备早餐 / 整理冰箱
      requirement: 产品出现时博主已经在产品的天然使用场景里
    
    step_2: 近景特写产品 + 文本框字幕
      duration: 2 秒
      visual: 产品包装清晰可见
    
    step_3: 自然口播功能描述
      example: 「这是我最近新发现的一个神器,不用像之前一样自己调味」
      tone: 用「神器」「方便」「直接」3 个具体功能词
      forbidden: 不要用「绝绝子」「真的好用」「冲」
    
    step_4: 第一视角动作 + 感官反馈
      example: 拌一拌 + 闻一下表情 + 「好香」
      duration: 3-5 秒
    
    step_5: 回到原本叙事
      requirement: 产品没有打断主叙事,而是融进去
  
  duration_total: 15-25 秒
```

## 八、结尾风格

```yaml
ending_style:
  pattern: 不强行 CTA,留白式收尾
  examples:
    - 「明天光线好的时候再展示」
    - 「计划赶不上变化,但生活就是这样」
    - 「今天就喝这么多,明天再做一盆」
  
  forbidden_endings:
    - 「冲冲冲快下单」
    - 「家人们点点关注」
    - 「评论区告诉我你想看什么」(凑活活极少这样硬要互动)
```

## 九、近期代表笔记参考

```yaml
reference_note:
  title: 老乡,人生可以是星露谷
  link: 见 references/screenshots/couhuohuo-note-1.png
  performance:
    estimated_views: 830000
    likes: 12000
    comments: 6494
    interaction_rate: 12.15%
  
  why_referenced: |
    本笔记完整体现了凑活活的 5 段式结构、玩梗式品牌别名(老演员冷冻麻辣烫)、
    具体感官描述(淡淡的麦芽香)、自嘲松弛(装大象一样 3 步)、
    产品植入路径(家乐麻酱拌面汁出现在做麻辣烫场景中)。
    脚本生成时以此为主要参考。
```

## 十、合规风险提示(本博主特有)

```yaml
compliance_specific_to_this_creator:
  - 凑活活粉丝活跃在凌晨 12-1 点,内容里偶尔有「失眠」「熬夜」相关吐槽。
    脚本中必须避免把「轻醒」跟「失眠后第二天补救」这类负面健康场景关联。
  - 她的玩梗式品牌别名虽然是她的语言特征,但「轻醒」作为新品牌建立中,
    第一次出现时建议正名一次,避免别名喧宾夺主。
  - 她偶尔会出现轻量级博主互文,但不能让她暗示其他酸奶品牌,
    避免品牌竞争方面的口碑风险。
```
