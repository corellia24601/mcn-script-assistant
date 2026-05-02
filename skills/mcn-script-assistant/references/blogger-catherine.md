# 博主风格档案 · @Catherine是小熊

> 本档案用于 SKILL.md 中的 Step 2「博主风格档案加载」环节。它的目的不是描述博主,而是让脚本生成 LLM 能模仿出博主调性。

---

## 一、基础信息

```yaml
profile:
  id: catherine_xiaoxiong
  display_name: Catherine是小熊
  platform: 小红书
  fans: 75900
  fan_demographics:
    female_ratio: 90.0%
    age_18_24: 44.0%
    age_25_34: 44.4%  # 6 位候选里最高,与 brief 主力人群最匹配
  active_hours: 18-24 点(下班时段)

content_role: brief 直接命中
matching_strategy: |
  人设「互联网打工人」直接对应 brief 的「上班族效率生活」,
  是 6 位候选里唯一一个能在 brief 文字层面找到精确对应的博主。
  其他博主都在「邻近」brief 的人群,只有她「就是」brief 写的那群人。
  跟凑活活形成「紧凑工位 vs 松弛日常」的互补叙事。
```

## 二、人设核心(脚本生成时必须保留)

```yaml
persona_core:
  identity: 互联网公司女性打工人,精致中带松弛
  emotional_tone: 自嘲式接受 / 戏剧化夸张 / 生活有仪式感但不紧绷
  not_about:
    - 不是「正能量职场博主」
    - 不是「自律晨间博主」
    - 不是「商业精英人设」
  about:
    - 是「写脑爆材料一边摸鱼一边交差的真实打工人」
    - 「忙着啃手都没空打字」式的真实感

forbidden_persona_drift:
  - 不要把她写成「健康博主」
  - 不要让她讲「持续运动 21 天」「饮食打卡」
  - 不要让她说「家人们」「OMG」「绝绝子」「冲冲冲」
  - 不要让她做正经的产品科普(违背她戏谑式语言风格)
```

## 三、视频结构模板(打工日记三段式)

```yaml
# 博主常态笔记时长
typical_note_duration:
  range: 2.5-3.5 分钟(150-210 秒)
  reference_note_duration: 3 分 09 秒(《谁不想在周一也清爽松软》)
  product_segment_duration_in_reference: 约 20 秒(多芬沐浴露植入,占完整笔记 10.5%)

# 商单脚本交付定义(重要)
deliverable_definition:
  total_script_duration: 60-90 秒(项目硬性要求)
  product_segment_duration: ≤30 秒(MCN 业务最佳实践)
  non_ad_segments_duration: 30-60 秒(用补全的博主调性内容填充)
  
  what_blogger_must_film: 产品植入段(脚本中标注「核心交付」的部分)
  what_blogger_can_adjust: 非广内容段(脚本中标注「参考方向」的部分,博主可按当下生活素材调整)
  total_blogger_note_length: 博主可在 60-90 秒里完整呈现,也可作为她常态 2.5-3.5 分钟笔记的一部分

# 非广内容素材池(用于补全段,避免照搬原笔记)
non_ad_content_palette:
  # 这些是 Catherine 常态会拍但参考笔记《周一清爽松软》里没出现过的场景类型
  # 写补全段时从这里取材,而不是抄原笔记的「写脑爆材料/魔大食堂/泰式按摩」
  
  morning_segment_alternatives:
    - 早晨闹钟前自然醒 vs 闹钟逼醒的对比戏
    - 化妆台上挑今天戴哪副耳环的小纠结
    - 从衣柜挑衣服时对自己说「今天穿这个 OK 吗」
    - 给绿植浇水时跟绿植说话
    - 起床后第一眼看到镜子里头发的反应
    - 试穿一件昨天买的衣服走两步
    - 翻冰箱看有什么能吃的(产品可在这里自然出现)
  
  workplace_segment_alternatives:
    - 下午 3 点会议室抢咖啡的内心戏
    - 同事问你周末干嘛了,你瞎编一个
    - 工位上的小植物今天好像歪了
    - 改 PPT 改到第 8 版的精神状态
    - 楼下便利店买关东煮的纠结(选哪几串)
    - 跟旁边工位同事互相吐槽天气
    - 收到一个莫名其妙的会议邀请
  
  off_work_segment_alternatives:
    - 下班路上走错地铁口的小尴尬
    - 进家门第一件事(脱鞋/瘫沙发/开灯/喂猫等)
    - 周三晚上不想做饭点了一个外卖
    - 翻购物车决定哪个先下单
    - 刷剧选择恐惧症
    - 看到楼下有人遛狗停下来看
  
  # 镜头组合提示
  visual_combinations:
    - 前置自拍 + 戏剧化表情 + 脸部变形滤镜
    - 第三视角全身入镜 + fit check 对镜
    - 物品近景特写(不一定是产品)+ 文本框字幕吐槽
    - 画中画对比(把当前状态跟历史/想象状态对比)

# 完整笔记的内容结构(供博主理解)
classic_three_segments:
  - segment: 起床段
    time_ratio: 0-33% of full note
    content: 清晨自律行动 + 早餐 + 洗护产品
    key_role: 这是产品植入的黄金位置(植入段落嵌入这里)
    typical_scenes:
      - 哑铃锻炼 / 芭蕾动作
      - 简单早餐(蓝莓、树莓等水果)
      - 沐浴 / 护肤
  
  - segment: 上班段
    time_ratio: 33-67% of full note
    content: 工位日常 + fit check + 会议吐槽
    typical_scenes:
      - 通勤
      - 工位办公
      - 会议室
      - fit check 对镜自拍
  
  - segment: 下班段
    time_ratio: 67-100% of full note
    content: 吃饭 / 按摩 / 购物等放松场景 + 回扣早晨产品
    key_role: 产品在结尾被回扣一次,首尾呼应

signature_structure: 早晨植入 + 结尾回扣
significance: |
  Catherine 的标志性结构是「早晨植入 + 结尾回扣」式双重曝光。
  我们的脚本要写的是:起床段的植入(20-25 秒) + 下班段的结尾回扣(5 秒以内一句口播)。
  其他部分博主自由发挥。
```

## 四、开场钩子模板

```yaml
opening_hook:
  pattern: 5-6 个生活片段快闪 + 网络热门动感 BGM,无配音
  
  shots_in_first_5_seconds:
    - 走路仰拍上半身
    - 锻炼某个动作
    - 拿到新物品
    - 工位办公
    - fit check 对镜
    - 下班放松场景(按摩/吃饭)
  
  rule: |
    这 5-6 个镜头实际上是「视频后续会出现的所有场景」的预告。
    节奏比凑活活更快(4-5 秒切完),纯靠 BGM 节奏带情绪。
  
  title_pattern:
    structure: 反问句式 / 自定义新词 / 具体感官词
    examples:
      - 「谁不想在周一也清爽松软!(早起脑爆日)」
      - 「写脑爆材料的早起日穿什么」
      - 「打工人精神好的一天从 XX 开始」
    rules:
      - 反问句式天然引发自我代入
      - 自定义词汇有标签感(「早起脑爆日」「XX 日」)
      - 具体感官词比「好状态」「精神」更有画面感
  
  forbidden_openings:
    - 「家人们,今天给大家分享一款好物」
    - 任何带画外音先解释的开场
```

## 五、镜头语言

```yaml
camera_language:
  shot_types_and_ratios:
    front_camera_selfie:
      ratio: 40%  # Catherine 的核心识别特征
      use_for: 边走边拍上半身、对镜头说话、口播
      requirement: 这一比例是必须保证的,低于 30% 会失去她的个人调性
    
    third_person_medium:
      ratio: 25%
      use_for: 展示穿搭、工位、动作
    
    picture_in_picture:
      ratio: 5%
      use_for: 小窗口画中画对比(如把另一个视频放在右上角形成对比笑点)
      example: 把欧阳春晓天鹅湖芭蕾视频放右上角,自己锻炼放主画面
    
    facial_filter_with_distortion:
      ratio: 10%
      use_for: 制造戏剧化夸张效果,降低广告感
    
    workplace_close_up:
      ratio: 20%
      use_for: 键盘打字、屏幕、咖啡杯等
  
  visual_effects:
    use:
      - 脸部变形滤镜(她的核心视觉风格之一)
      - 电子配音特效(配合特定吐槽片段)
      - 画中画对比
      - 网络热门 BGM
    note: |
      Catherine 对小红书/抖音流行内容的复用速度极快,
      写她的脚本时文案不能太「永恒」,可以加入当下流行的网络梗。
```

## 六、语言风格(核心识别特征)

```yaml
language_style:
  identifying_features:
    
    # 特征 1: 谐音梗 + 自嘲式时尚术语
    pun_with_self_deprecation:
      examples:
        - 「欧阳春晓 为何:我舞得不美?」
        - 「真的是太 duang 了」
        - 「翻一个包」(翻包视频流行 meme 的反向使用)
      replication_rule: 用一个流行梗的反向/自嘲版本
    
    # 特征 2: 职场黑话戏谑
    workplace_jargon_play:
      description: 把职场词玩成段子,精确描绘「打工人」身份
      examples:
        - 「写脑爆材料」
        - 「左右脑互搏」
        - 「把自己的观点一脚踹飞然后再给它拼起来反复论证」
        - 「啥都想深入的摸鱼时刻突然变得十分的神圣」
        - 「魂穿中学时代」
      replication_rule: |
        脚本中必须有 1-2 处「打工人黑话」。
        for 「轻醒」: 
        - 「脑爆前先垫一勺,大脑感觉被点亮了」
        - 「下午会议又又又开,但好歹早上的酸奶还在撑场子」
        - 「会议室空调太冷,酸奶在肚子里是暖的」
    
    # 特征 3: 比喻 + 身体感受
    metaphor_and_bodily_sensation:
      description: 描述产品始终用「比喻 + 身体感受」,不直接说产品好用
      examples:
        - 「像到了海边一样」
        - 「我现在就是一口水润大柚子」
        - 「香香软软的小女孩」
      replication_rule: |
        描述「轻醒」希腊酸奶用比喻而非形容词:
        - 「一勺下去像在嘴里小睡了一下」
        - 「黄桃丁咬到的瞬间像周二突然变成周五」
        - 「酸度刚刚好,像被人轻轻拍醒」
    
    # 特征 4: 碎片化吐槽
    fragmented_complaints:
      description: 让产品植入夹在生活吐槽中间,出现得不突兀
      examples:
        - 「我们楼里的空调真的是太冷了」
        - 「忙着啃手都没空打字」
        - 「今天的哑铃有点太重了,真的是太 duang 了」
      replication_rule: 脚本里 1 处「碎片化吐槽」与产品擦边出现
    
    # 特征 5: 网络热门梗时效性强
    trending_meme_speed:
      description: 对小红书/抖音流行内容的复用速度极快
      examples:
        - 脸部变形滤镜
        - 电子配音
        - 当下热门 BGM
      replication_rule: |
        写她的脚本时,文案不能太「永恒」,
        可以加入当下流行的网络梗(如最近的「脑爆日」「魂穿」等)。
```

## 七、产品植入路径(本博主的标准模板)

```yaml
product_insertion:
  position_in_full_note: 起床段中部(完整笔记的 30-45 秒区间)
  insertion_segment_duration: 20-25 秒(我们脚本要写的核心部分)
  ending_callback_duration: 3-5 秒(我们脚本要写的回扣部分,嵌入博主的下班段结尾)
  total_brand_exposure: ≤30 秒(植入段 + 回扣段的总时长上限)
  
  signature_structure: 早晨植入 + 结尾回扣(双重曝光)
  
  morning_insertion_steps:
    step_1: 博主自然过渡
      example: 「我现在要准备 X」(产品出现前必有过渡句)
      forbidden: 不能直接切到产品镜头
    
    step_2: 第一视角展示产品
      duration: 1-2 秒
      visual: 拿起产品,镜头停留
    
    step_3: 包装/质地特写
      duration: 2-3 秒
      visual: 至少 2 个特写镜头(如希腊酸奶的拉丝镜头、挖一勺立起来的镜头)
    
    step_4: 使用场景 + 感官描述
      structure: 4 个感官词层层递进
      example_for_target_product: 「酸度柔但奶味厚 / 黄桃丁咬开就甜 / 一勺挖起来还立着不滴 / 像被人轻轻拍醒」
    
    step_5: 戏剧化插入镜头(可选)
      example: 2 秒插入一个具象化比喻的镜头(如说「像被拍醒」时插入闹钟特写)
    
    step_6: 效果展示
      example: 镜头展示「现在的我」(精神状态、身体状态)
  
  ending_callback_steps:
    # 这一步是 Catherine 的标志性产品闭环,必须保留
    requirement: 视频结尾用一句话回扣产品
    example_for_target_product:
      - 「下午三点居然没饿,大概就是早上那杯酸奶在帮我撑场子」
      - 「按摩阿姨说我今天精神特别好,大概是早上那勺酸奶的功劳」
      - 「下班路上没去抢奶茶,因为肚子还在被早上的酸奶罩着」
  
  duration_total: 20-30 秒(植入段 20-25 秒 + 结尾回扣 3-5 秒)
```

## 八、结尾风格

```yaml
ending_style:
  pattern: 戏剧化感受 + 自嘲式总结 + 产品回扣
  examples:
    - 「我不会是睡美人吧」
    - 「按摩阿姨夸我是香香软软的小女孩」
    - 戏剧化身体感受词
  
  forbidden_endings:
    - 「冲冲冲快下单」
    - 「家人们点点关注」
    - 任何硬广式 CTA
  
  rule: |
    结尾必须有「身体感受/状态/夸赞」式的戏剧化收束,
    不能用平铺直叙的结尾。
```

## 九、近期代表笔记参考

```yaml
reference_note:
  title: 谁不想在周一也清爽松软!(早起脑爆日)
  link: 见 references/screenshots/catherine-note-1.png
  performance:
    estimated_views: 14000
    likes: 1248
    comments: 126
    interaction_rate: 8.8%
  
  why_referenced: |
    本笔记完整体现了 Catherine 的三段式结构(起床/上班/下班)、
    早晨植入 + 结尾回扣的双重曝光路径、
    谐音梗 + 职场黑话语言风格(脑爆日、写脑爆材料、左右脑互搏)、
    比喻 + 身体感受的种草表达(像海边、水润大柚子、香香软软小女孩)。
    脚本生成时以此为主要参考。
```

## 十、合规风险提示(本博主特有)

```yaml
compliance_specific_to_this_creator:
  - Catherine 偶尔会有「快点穿上小吊带」「让肉肉早点消失」式的轻量身材吐槽。
    脚本中必须避免把「轻醒」跟「身材管理」「让肉肉消失」等任何减肥联想关联。
  - 她的内容里出现过「写脑爆材料」「啥都想深入的摸鱼时刻」等职场吐槽,
    脚本中可以保留这种戏谑感,但不能延伸到「替代正餐」「替代咖啡」等功能性宣称。
  - 评论区有相当部分粉丝问穿搭链接,植入「轻醒」时不能跟服饰品牌或穿搭话题混杂,
    避免粉丝注意力跑偏。
```
