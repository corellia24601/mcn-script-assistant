"""
run_pipeline.py - 端到端运行 mcn-script-assistant Skill

把 SKILL.md 描述的 6 步流程串起来,可以独立调用,也可以作为 Coze 工作流的兜底实现。

流程:
    Step 1: 加载 brief.md → 结构化 brief
    Step 2: 加载 blogger profile → 提取风格档案
    Step 3: 调用 LLM 生成脚本(需要 ANTHROPIC_API_KEY)
    Step 4: 从脚本派生分镜表
    Step 5: 调用 risk_check.py 质检
    Step 6: 调用 write_to_feishu.py 写入(可选)

用法:
    python run_pipeline.py --blogger catherine_xiaoxiong
    python run_pipeline.py --blogger couhuohuo --no-feishu
    python run_pipeline.py --blogger catherine_xiaoxiong --regenerate-on-fail 2
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 让本地 import 工作
sys.path.insert(0, str(Path(__file__).parent))

# 启动时自动加载仓库根 .env
try:
    from dotenv import load_dotenv  # noqa: E402
    _repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(_repo_root / ".env", override=False)
except ImportError:
    pass

from risk_check import check_script  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent           # skill 目录，留给 references/
REPO_ROOT = Path(__file__).resolve().parents[3]      # 仓库根，输出统一放这里
REFERENCES_DIR = PROJECT_ROOT / "references"
OUTPUT_DIR = REPO_ROOT / "output"


# -------- Step 1: Brief 拆解 --------

def load_brief() -> dict:
    """从 references/brief.md 提取所有 yaml 块,合并为单个 dict。"""
    brief_path = REFERENCES_DIR / "brief.md"
    text = brief_path.read_text(encoding="utf-8")
    
    # 简化:直接把所有 yaml 块原样返回为字符串,让 LLM 自己理解
    # 因为 brief.md 里的 yaml 跨多个区块,合并需要 PyYAML 而且容易出错
    yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", text, flags=re.DOTALL)
    
    return {
        "raw_yaml_concatenated": "\n\n".join(yaml_blocks),
        "source_path": str(brief_path),
    }


# -------- Step 2: 博主档案加载 --------

def load_blogger_profile(blogger_id: str) -> str:
    """加载博主档案的原始内容,直接喂给 LLM。"""
    # 同时支持 blogger-{full_id}.md / blogger-{short}.md / {id}.md 等命名
    short_id = blogger_id.split("_")[0]  # catherine_xiaoxiong → catherine
    candidates = [
        REFERENCES_DIR / f"blogger-{blogger_id}.md",
        REFERENCES_DIR / f"blogger-{short_id}.md",
        REFERENCES_DIR / f"{blogger_id}.md",
        REFERENCES_DIR / f"{short_id}.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    
    raise FileNotFoundError(
        f"找不到博主档案。已尝试: {[str(p) for p in candidates]}\n"
        f"请确保 references/blogger-{blogger_id}.md 存在"
    )


# -------- Step 3: 脚本生成 --------

def build_generation_prompt(brief: dict, blogger_profile: str) -> str:
    """构造给 LLM 的 prompt。"""
    return f"""你是一位资深的 MCN 内容策划,专门为小红书品牌商单撰写短视频脚本。

# ⚠️ 最重要的核心规则(违反任何一条都会被拦截重生成)

## 规则 1: 产出 60-90 秒完整脚本,其中植入段 ≤30 秒

**总时长**: 60-90 秒(项目硬性要求,不可少于 60 秒)
**产品植入段**: ≤30 秒(MCN 业务硬约束,目标 20-25 秒)
**非广内容段**: 30-60 秒(用模仿博主调性的内容补全)

## 规则 2: 脚本里的两类段落必须明确区分

每个段落必须标注它的状态:

- **核心交付段**(产品植入相关): 博主必须按脚本拍,品牌方为这部分付费,这部分要保证质量和合规
- **参考方向段**(非广内容补全): 博主可以参考也可以用她当下的生活素材替换,但需保持调性

输出 JSON 时,在 `body` 数组的每个段落上加 `segment_type: "core_delivery"` 或 `"reference_only"` 字段。

## 规则 3: 非广内容段必须避免照搬博主已有笔记

❌ 严禁出现的具体场景(因为博主参考笔记里已有,会显得我们在抄她):

**Catherine 的禁用场景**:
- 「写脑爆材料」「左右脑互搏」(可作为语言风格参考,但不能作为新脚本的核心剧情)
- 「魔大食堂厚切三文鱼」(具体餐厅名)
- 「泰式按摩」「香香软软的小女孩」(原笔记结尾梗)
- 「欧阳春晓 为何我舞得不美」(原笔记画中画梗)

**凑活活的禁用场景**:
- 「米露」「揉米」「韩料店」(具体食物)
- 「冷冻麻辣烫」「家乐麻酱拌面汁」(已是原笔记核心场景)
- 「星露谷物语挖野葱」「煤矿森林」(原笔记 plot)
- 「水晶手串」(原笔记结尾梗)

✅ 应该的做法:从博主档案的 `non_ad_content_palette` 字段里取**新场景**,
应用博主的语言风格识别特征(谐音梗 / 自嘲松弛 / 具体感官词等)写出来。

## 规则 4: 严格控制植入时长

植入段(包括过渡 + 产品出现 + 感官描述 + 动作镜头 + 结尾回扣)所有相关内容加起来 ≤30 秒。
如果 60 秒脚本,植入段 25 秒,非广段就只有 35 秒——这是合理的。
如果 90 秒脚本,植入段 25 秒,非广段就有 65 秒——这也合理。
**不要为了写满 90 秒就把植入段拉长到 50 秒**——总时长靠非广段补,不靠拉长植入段。

## 规则 5: 口播台词不要连读「品牌名 + 产品类目」全称

❌ 禁用: 「轻醒酸奶」「轻醒希腊酸奶」「轻醒高蛋白酸奶」(品牌+品类连读 = 广告感)

✅ 推荐: 
- 「这个酸奶」「这罐子」「我最近发现的这个」(替代指称)
- 「叫轻醒」(单独提品牌名,不带类目)
- 「黄桃口味的」「希腊味的」(用口味或品类指称)
- 把「轻醒」两字玩梗:「轻醒,名字起得还挺准的」「轻轻醒醒小酸奶」

## 规则 6: 标题 + 开场 10 秒 + 前 2 个分镜不能指向产品

❌ 禁用的标题:
- 「打工人精神好的一天从这勺开始」(「这勺」直接指产品)
- 「i 人下班吃这个真的会上瘾」(「这个」+「上瘾」=带货语)
- 任何含「这一杯」「这一罐」「这一勺」的标题

✅ 推荐的标题:
- 「打工人精神好的秘诀(早起脑爆日)」(指向状态,不指产品)
- 「今天 7 点自己醒了,还有比这更好的事吗」(指向情绪,不指产品)
- 「i 人下班日记 | 今天躺在地毯上」(指向场景,不指产品)

开场 10 秒(前 2 个分镜):
- 画面: 不要出现产品近景特写或品牌字样清晰可见的镜头(可以远景出现产品但拉远到看不清字)
- 口播: 不要明确指向产品(「今天给大家分享」「这个真的是宝藏」都不行)
- 应该: 引入博主当天的状态、心情、小事件,产品在博主内容自然进展到「该出现」时再出现

## 规则 7: 严禁违禁词和功能性宣称

严禁:减肥、瘦、瘦身、减脂、燃脂、降糖、控糖、治疗、最、第一、100%、补充蛋白质、增肌、替代正餐、控住、暴瘦
软化措辞:「饱腹感」必须配「适合早上吃完比较扛饿」式语境,不能孤立使用

## 规则 8: 卖点分层处理(强约束)

不是 brief 里所有卖点都要硬塞进口播。按博主档案 `audience_alignment_with_brief` 的评估,把卖点分三层:

**主打卖点(口播深度种草)**: 博主必须念出来,作为产品段口播的核心
- 凑活活的主打:在家自用 / 早午餐场景 / 低负担(松弛语境) / 饱腹感(扛饿语境)
- Catherine 的主打:早餐场景 / 饱腹感(打工人不饿到 10 点) / 下午茶替代奶茶

**次要卖点(画面浅触达)**: 通过包装字样/字幕/产品特写体现,博主不口播
- 高蛋白(包装字样可见即可,博主不主动说「补充蛋白质」)
- 0 蔗糖(包装字样可见即可,博主不主动说「控糖」)

**不覆盖卖点(本次合作放弃)**: 不强行塞,留给后续投放阶段
- 健身/运动后(博主调性不匹配,强塞会破坏调性)
- 控糖/适合糖尿病(违规)

## 规则 9: 职业场景拍摄红线(强约束 - 真实合规问题)

这不是平台审核问题,是博主跟雇主签的真实 NDA / 劳动法约束,博主自己拍出来会有风险。

**Catherine 类(拍工位日常)严禁**:
- 工位屏幕显示具体内容(具体邮件 / 文档 / 聊天 / 代码 / 数据 / 客户名 / 任何可识别真实业务的内容)
- 显示具体公司名 / logo / 工牌
- 具体客户名 / 项目代号 / 真实业务术语
- 会议室白板内容 / 同事容貌
- ❌ 不能写:「工位屏幕特写:屏幕上密密麻麻的文档」、「屏幕上 PPT 字幕飘过」、「鼠标在颜色选择器上点了深蓝色」、「键盘上敲的代码」、「PPT 改到第七版的具体页面」、「Excel 表格特写」、「邮件预览」
- ✅ 可以写:键盘鼠标手部特写、咖啡杯绿植摆件、办公楼大堂走廊、模糊屏幕背景、屏幕上方浮出后期字幕、手机屏幕上插入比喻字幕

**凑活活类(拍做饭/吃东西)严禁**:
- 出现其他酸奶/同品类竞品包装(冰箱镜头需提前清场)
- 可识别的餐厅名/外卖品牌
- 给食物附带「健康」「促消化」「养胃」等功效宣称

---

# 客户 Brief(包含合规约束、植入比例、品牌名规范、开场反硬广四大约束的完整 YAML)

```yaml
{brief['raw_yaml_concatenated']}
```

# 目标博主风格档案

{blogger_profile}

---

# 任务

为该博主生成一条 60-90 秒完整脚本。脚本由「核心交付段(产品植入,≤30 秒)」+「参考方向段(博主调性补全,30-60 秒)」组成。

**强制规则补充**:
1. **博主调性 > 品牌诉求**:必须保留博主原本的语言习惯、镜头偏好
2. **博主语言模板**:必须命中博主档案中至少 3 个语言风格特征
3. **感官描述**:产品描述必须用具体感官词或比喻,**禁用「真的好喝」「绝绝子」「YYDS」**
4. **场景真实性**:产品出现时博主已在产品天然使用场景里,先有「我现在要 X」过渡句
5. **非广内容素材必须新鲜**:从博主档案 `non_ad_content_palette` 取材,不复用原参考笔记的具体场景
6. **卖点分层**:按博主 `audience_alignment_with_brief` 的 `recommended_selling_points_to_emphasize` 主打,不要硬塞 out_of_scope 的卖点
7. **工位场景反 NDA**:Catherine 的工位画面只拍键盘/咖啡杯/绿植/手部/楼道,不拍屏幕具体内容/公司名/客户名/真实业务

# 输出格式

只返回符合以下结构的 JSON,不要任何其他文字或代码块标记:

```json
{{
  "title": "20 字内,符合博主标题模板,不能指向产品",
  "duration_seconds": 75,
  "product_segment_duration_seconds": 25,
  "non_ad_segments_duration_seconds": 50,
  
  "body": [
    {{
      "timestamp": "0-15s",
      "segment_type": "reference_only",
      "segment_label": "开场段(参考方向)",
      "voiceover": "口播文案",
      "shot_description": "画面描述",
      "based_on_palette_item": "(可选)取材自 non_ad_content_palette 的哪一项"
    }},
    {{
      "timestamp": "15-40s",
      "segment_type": "core_delivery",
      "segment_label": "产品植入段(核心交付)",
      "voiceover": "包含过渡句+感官描述+动作的完整口播",
      "shot_description": "包含产品包装特写+质地特写+动作镜头",
      "transition_line": "我现在要 X",
      "sensory_description": "至少 1 个比喻 + 1 个具体感官词",
      "action_shots": ["动作1", "动作2", "动作3"]
    }},
    {{
      "timestamp": "40-75s",
      "segment_type": "reference_only",
      "segment_label": "中后段(参考方向)",
      "voiceover": "口播文案",
      "shot_description": "画面描述",
      "based_on_palette_item": "(可选)取材自 non_ad_content_palette 的哪一项"
    }}
  ],
  
  "ending_callback": {{
    "applicable_to": "Catherine 必填 / 凑活活留空",
    "voiceover": "嵌入结尾的一句产品回扣口播,5 秒以内,合规"
  }},
  
  "compliance_notes": [
    "本脚本拍摄时博主需要注意的措辞 1",
    "本脚本拍摄时博主需要注意的措辞 2"
  ],
  
  "reasoning_check": {{
    "title_avoids_product_pointer": "确认标题没有「这勺」「这一杯」类指向词",
    "opening_no_product": "确认开场 10 秒和前 2 个分镜不指向产品",
    "no_brand_full_name_in_voiceover": "确认口播没有「轻醒酸奶」类全称连读",
    "product_segment_within_30s": "确认 segment_type=core_delivery 的段落总时长 ≤30 秒",
    "non_ad_segments_avoid_copying": "确认非广段没有照搬原笔记的「写脑爆材料/魔大食堂/米露/挖野葱」等已有场景",
    "total_duration_60_to_90": "确认总时长在 60-90 秒之间",
    "selling_points_layered": "确认按博主对齐度主打 primary_selling_points,没有硬塞 out_of_scope 卖点",
    "no_workplace_screen_content": "(Catherine 限定)确认没有出现工位屏幕具体内容/公司名/客户名/真实业务术语",
    "ending_callback_not_duplicated_in_body": "确认 body 数组里没有 segment_type=core_delivery 的「结尾回扣段」（结尾回扣只在顶层 ending_callback 字段写一次）",
    "voiceover_density_matches_timestamp": "确认每段 voiceover 字数 ≈ timestamp 秒数 × 5（不发空、不冗长）"
  }}
}}
```

只返回 JSON,不要 markdown 代码块标记,不要解释。
"""


def call_claude_for_script(prompt: str, api_key: str | None = None) -> dict:
    """调用 Claude 生成脚本。"""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "需要 ANTHROPIC_API_KEY 环境变量才能调用 Claude 生成脚本。\n"
            "设置方法: export ANTHROPIC_API_KEY='your_key_here'"
        )
    
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("缺少依赖: pip install anthropic")
    
    client = anthropic.Anthropic(api_key=api_key)
    # 模型名走 env（CLAUDE.md 要求），默认 sonnet-4-6
    model = os.environ.get("ANTHROPIC_MODEL_PRIMARY", "claude-sonnet-4-6")
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    
    text = response.content[0].text.strip()
    # 去除可能的 markdown 代码块标记
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM 返回的不是合法 JSON: {e}\n原文:\n{text[:500]}")


# -------- Step 4: 分镜表派生 --------

def derive_storyboard(script: dict) -> list[dict]:
    """从「带 segment_type 的 body 数组」脚本派生分镜表（v2 去重版）。

    每段 body 1-2 镜：≤8s 拆 1 镜，>8s 拆 2 镜。不再硬拆 3 镜，画面
    层级靠 shot_description 字符串里的「①②③」标号自带表达。

    body 里 segment_label 含「结尾回扣/回扣/callback/ending」的段被跳过——
    顶层 ending_callback 字段会单独渲染 1 镜，避免双写。
    """
    storyboard = []
    shot_num = 1
    body = script.get("body", [])

    _CALLBACK_LABEL_KEYWORDS = ("结尾回扣", "回扣", "callback", "ending")

    def _add(duration, type_label, visual, voiceover, props, difficulty):
        nonlocal shot_num
        storyboard.append({
            "shot_number": shot_num,
            "duration_seconds": duration,
            "segment_type": type_label,
            "visual_description": visual,
            "voiceover_or_subtitle": voiceover,
            "props_and_scene": props,
            "shooting_difficulty": difficulty,
        })
        shot_num += 1

    for segment in body:
        seg_type = segment.get("segment_type", "reference_only")
        seg_label = segment.get("segment_label", "")

        # 跳过结尾回扣段（顶层 ending_callback 会单独渲染）
        if seg_type == "core_delivery" and any(kw in seg_label for kw in _CALLBACK_LABEL_KEYWORDS):
            continue

        timestamp = segment.get("timestamp", "")
        m = re.match(r"(\d+)-(\d+)s", timestamp)
        seg_duration = int(m.group(2)) - int(m.group(1)) if m else 10

        type_label = "核心交付" if seg_type == "core_delivery" else "参考方向"
        difficulty_prefix = "" if seg_type == "core_delivery" else "(参考方向)"
        difficulty = "中" if seg_type == "core_delivery" else "低(博主可调整)"
        voiceover = segment.get("voiceover", "")
        visual = segment.get("shot_description", "")
        palette_item = segment.get("based_on_palette_item", "")
        props = f"{seg_label}{(' / 取材自:' + palette_item) if palette_item else ''}"

        sub_count = 1 if seg_duration <= 8 else 2
        sub_dur = max(seg_duration // sub_count, 3)

        if sub_count == 1:
            _add(seg_duration, type_label, f"{difficulty_prefix}{visual}".strip(), voiceover, props, difficulty)
        else:
            half = len(voiceover) // 2
            _add(sub_dur, type_label, f"{difficulty_prefix}{visual}".strip(),
                 voiceover[:half], props, difficulty)
            _add(seg_duration - sub_dur, type_label, f"{difficulty_prefix}{visual}".strip() + "（接上）",
                 voiceover[half:], props, difficulty)

    # 顶层 ending_callback 单独 1 镜（如果有）
    callback = script.get("ending_callback", {}) or {}
    cb_voice = callback.get("voiceover", "")
    if cb_voice:
        _add(5, "核心交付",
             "嵌入结尾的产品轻量回扣（如包里随手拿出产品晃一下，或字幕浮出回扣口播）",
             cb_voice, "博主结尾场景 + 轻醒罐子", "低")

    return storyboard


# -------- Step 6: 飞书写入(可选)--------

def write_to_feishu_optional(script: dict) -> dict | None:
    """如果飞书凭证齐全,写入飞书。否则跳过。"""
    if not all(os.environ.get(k) for k in [
        "FEISHU_APP_ID", "FEISHU_APP_SECRET",
        "FEISHU_BITABLE_APP_TOKEN", "FEISHU_BITABLE_TABLE_ID"
    ]):
        print("⚠️  飞书凭证未完整配置,跳过 Step 6")
        return None
    
    from write_to_feishu import write_script_to_bitable, build_record_url
    
    record = write_script_to_bitable(script)
    url = build_record_url(
        os.environ["FEISHU_BITABLE_APP_TOKEN"],
        os.environ["FEISHU_BITABLE_TABLE_ID"],
        record.get("record_id", ""),
    )
    print(f"✓ 已写入飞书: {url}")
    return record


# -------- 主流程 --------

def run_pipeline(
    blogger_id: str,
    no_feishu: bool = False,
    regenerate_on_fail: int = 1,
) -> dict:
    """端到端运行 6 步流程。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"━━━ MCN 脚本生成 Pipeline ━━━")
    print(f"目标博主: {blogger_id}")
    print()
    
    # Step 1
    print("→ Step 1: 加载 brief...")
    brief = load_brief()
    
    # Step 2
    print(f"→ Step 2: 加载博主档案...")
    blogger_profile = load_blogger_profile(blogger_id)
    
    # Step 3 + 5: 生成 + 质检,失败重试
    script = None
    final_report = None
    
    for attempt in range(1, regenerate_on_fail + 2):
        print(f"→ Step 3: 生成脚本 (attempt {attempt}/{regenerate_on_fail + 1})...")
        prompt = build_generation_prompt(brief, blogger_profile)
        script = call_claude_for_script(prompt)
        
        # 补充元信息
        script["script_id"] = str(uuid.uuid4())[:8]
        script["brand"] = "轻醒"
        script["creator"] = {"id": blogger_id, "display_name": _get_display_name(blogger_id)}
        script["generated_at"] = datetime.now().isoformat()
        
        # Step 4
        print("→ Step 4: 派生分镜表...")
        script["storyboard"] = derive_storyboard(script)
        
        # Step 5
        print("→ Step 5: 风险质检...")
        # 复用 load_blogger_profile 的查找逻辑找到实际路径
        short_id = blogger_id.split("_")[0]
        profile_path = None
        for candidate in [
            REFERENCES_DIR / f"blogger-{blogger_id}.md",
            REFERENCES_DIR / f"blogger-{short_id}.md",
        ]:
            if candidate.exists():
                profile_path = str(candidate)
                break
        
        report = check_script(
            script,
            forbidden_words_path=str(REFERENCES_DIR / "forbidden_words.md"),
            blogger_profile_path=profile_path,
            enable_llm_judge=False,  # 默认不启用,避免双倍 API 调用
        )
        script["compliance_report"] = report
        final_report = report
        
        print(f"   状态: {report['compliance_status']}")
        if report["extreme_words_hits"]:
            print(f"   命中违禁词: {[h['word'] for h in report['extreme_words_hits']]}")
        
        if report["compliance_status"] != "拦截":
            break
        
        if attempt <= regenerate_on_fail:
            print(f"   ⚠️  被拦截,准备重新生成...")
        else:
            print(f"   ✗ 重试次数耗尽,输出最后一版供人工 review")
    
    # 保存输出
    output_json = OUTPUT_DIR / f"final_script_{blogger_id}.json"
    output_md = OUTPUT_DIR / f"final_script_{blogger_id}.md"
    
    output_json.write_text(
        json.dumps(script, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output_md.write_text(format_script_as_markdown(script), encoding="utf-8")
    
    print(f"\n✓ 脚本已保存:")
    print(f"  JSON: {output_json}")
    print(f"  Markdown: {output_md}")
    
    # Step 6
    if not no_feishu:
        print("\n→ Step 6: 写入飞书...")
        write_to_feishu_optional(script)
    
    return script


def _get_display_name(blogger_id: str) -> str:
    """从博主档案里提取 display_name。简化:用映射表。"""
    name_map = {
        "catherine_xiaoxiong": "Catherine是小熊",
        "couhuohuo": "凑活活",
    }
    return name_map.get(blogger_id, blogger_id)


def format_script_as_markdown(script: dict) -> str:
    """把脚本格式化为人类可读的 Markdown(完整 60-90 秒脚本,区分核心交付/参考方向)。"""
    creator = script.get("creator", {}).get("display_name", "")
    
    lines = [
        f"# {script.get('title', '(无标题)')}\n",
        f"- **品牌**: {script.get('brand', '')}",
        f"- **博主**: {creator}",
        f"- **总时长**: {script.get('duration_seconds', '?')} 秒",
        f"- **核心交付段时长(产品植入)**: {script.get('product_segment_duration_seconds', '?')} 秒",
        f"- **参考方向段时长(博主调性补全)**: {script.get('non_ad_segments_duration_seconds', '?')} 秒",
        f"- **生成时间**: {script.get('generated_at', '')}",
        f"- **质检状态**: {script.get('compliance_report', {}).get('compliance_status', '?')}",
        "",
        "> 📌 **段落说明**:",
        "> - 「**核心交付**」段为产品植入相关内容,博主必须按脚本拍摄,品牌方为这部分付费",
        "> - 「**参考方向**」段为博主调性的非广内容,博主可按当下生活素材调整,只需保持调性一致",
        "",
        "## 完整脚本",
        "",
    ]
    
    body = script.get("body", [])
    for seg in body:
        seg_type = seg.get("segment_type", "reference_only")
        type_label = "🎯 **核心交付**" if seg_type == "core_delivery" else "💡 **参考方向**"
        timestamp = seg.get("timestamp", "")
        seg_label = seg.get("segment_label", "")
        
        lines.append(f"### [{timestamp}] {seg_label}")
        lines.append(f"")
        lines.append(f"**类型**: {type_label}")
        lines.append(f"")
        
        if seg_type == "core_delivery":
            lines.append(f"**过渡句**: {seg.get('transition_line', '')}")
            lines.append(f"")
            lines.append(f"**完整口播**:")
            lines.append(f"> {seg.get('voiceover', '')}")
            lines.append(f"")
            lines.append(f"**感官描述要点**: {seg.get('sensory_description', '')}")
            lines.append(f"")
            lines.append(f"**关键动作镜头**:")
            for shot in seg.get("action_shots", []):
                lines.append(f"- {shot}")
            lines.append(f"")
            lines.append(f"**画面**: {seg.get('shot_description', '')}")
        else:
            lines.append(f"**口播参考**:")
            lines.append(f"> {seg.get('voiceover', '')}")
            lines.append(f"")
            lines.append(f"**画面参考**: {seg.get('shot_description', '')}")
            if seg.get("based_on_palette_item"):
                lines.append(f"")
                lines.append(f"**取材自素材池**: {seg.get('based_on_palette_item', '')}")
        
        lines.append(f"")
    
    # 结尾回扣
    callback = script.get("ending_callback", {})
    if callback and callback.get("voiceover"):
        lines.extend([
            "## 结尾回扣(核心交付)",
            "",
            f"- **适用博主**: {callback.get('applicable_to', '')}",
            f"- **口播**: {callback.get('voiceover', '')}",
            "",
        ])
    
    # 分镜表
    lines.extend([
        "## 分镜表",
        "",
        "| # | 时长 | 类型 | 画面 | 口播/字幕 | 道具 | 难度 |",
        "|---|---|---|---|---|---|---|",
    ])
    for shot in script.get("storyboard", []):
        voiceover = str(shot.get("voiceover_or_subtitle", "")).replace("\n", " ").replace("|", "/")
        visual = str(shot.get("visual_description", "")).replace("\n", " ").replace("|", "/")
        seg_type = shot.get("segment_type", "")
        lines.append(
            f"| {shot.get('shot_number')} | {shot.get('duration_seconds')}s "
            f"| {seg_type} "
            f"| {visual[:100]} "
            f"| {voiceover[:100]} "
            f"| {shot.get('props_and_scene', '')} "
            f"| {shot.get('shooting_difficulty', '')} |"
        )
    
    # 合规
    lines.extend(["", "## 合规风险提醒", ""])
    for note in script.get("compliance_notes", []):
        lines.append(f"- {note}")
    
    # 生成自检
    rc = script.get("reasoning_check", {})
    if rc:
        lines.extend(["", "## 生成自检", ""])
        for k, v in rc.items():
            lines.append(f"- **{k}**: {v}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="运行 mcn-script-assistant 端到端流程")
    parser.add_argument("--blogger", required=True, help="博主 ID,如 catherine_xiaoxiong / couhuohuo")
    parser.add_argument("--no-feishu", action="store_true", help="跳过飞书写入")
    parser.add_argument("--regenerate-on-fail", type=int, default=1, help="质检失败时重生成次数")
    
    args = parser.parse_args()
    
    try:
        run_pipeline(
            blogger_id=args.blogger,
            no_feishu=args.no_feishu,
            regenerate_on_fail=args.regenerate_on_fail,
        )
        return 0
    except Exception as e:
        print(f"\n[X] Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
