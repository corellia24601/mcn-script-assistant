"""
risk_check.py - MCN 小红书脚本风险质检

被 SKILL.md 的 Step 5 调用。三层质检:
1. 极限词扫描(基于 references/forbidden_words.md)
2. 医疗/减肥承诺检测(规则引擎 + 可选 LLM 二次审查)
3. LLM-as-Judge 整体审查(可选,需要 Anthropic API key)

输入: 符合 references/output_schema.json 的脚本 JSON
输出: compliance_report 字段(同样符合 schema)

用法:
    python risk_check.py --script output/final_script.json --output output/compliance_report.json
    
或作为模块导入:
    from risk_check import check_script
    report = check_script(script_dict, forbidden_words_path="references/forbidden_words.md")
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# -------- 违禁词加载 --------

def load_forbidden_words(forbidden_md_path: str) -> dict[str, list[str]]:
    """
    从 forbidden_words.md 解析违禁词。
    
    解析逻辑:扫描 yaml 代码块,把每个 yaml 块下的列表项提取出来。
    分类按照 markdown 二级标题归组。
    """
    text = Path(forbidden_md_path).read_text(encoding="utf-8")
    
    categories: dict[str, list[str]] = {
        "extreme_words": [],
        "medical_claims": [],
        "weight_loss_claims": [],
        "glucose_claims": [],
        "false_promises": [],
        "platform_forbidden": [],
        "category_specific": [],
        "brand_specific": [],
    }
    
    # 匹配 yaml 代码块
    yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", text, flags=re.DOTALL)
    
    for block in yaml_blocks:
        # 跳过软化建议块和灰色地带块(它们结构不同)
        if "softening_suggestions" in block or "caution_zone" in block:
            continue
        
        # 提取每一行 - 开头的字符串
        lines = block.split("\n")
        current_category = None
        
        for line in lines:
            stripped = line.strip()
            
            # 识别 category 名
            if stripped.endswith(":") and not stripped.startswith("-"):
                key = stripped.rstrip(":").strip()
                if key in categories:
                    current_category = key
                elif key in ("forbidden_due_to_competitor_overlap", "forbidden_context_associations"):
                    current_category = "brand_specific"
                elif key in ("category_specific_dairy",):
                    current_category = "category_specific"
                continue
            
            # 提取列表项
            if stripped.startswith("- ") and current_category:
                word = stripped[2:].strip().strip('"').strip("'")
                # 跳过注释行
                if word.startswith("#") or not word:
                    continue
                # 去除中文括号注释(如「关键词(说明文字)」 → 「关键词」)
                word = re.sub(r"[((].*?[))]", "", word).strip()
                # 跳过描述性长句(>20 字)
                if len(word) > 20:
                    continue
                # 把「A」「B」 拆分成 A, B 两个词
                quoted_terms = re.findall(r"[「]([^」]+)[」]", word)
                if quoted_terms:
                    for term in quoted_terms:
                        if term and term not in categories[current_category]:
                            categories[current_category].append(term)
                elif word not in categories[current_category]:
                    categories[current_category].append(word)
    
    return categories


# -------- 极限词扫描 --------

# 这些短语包含违禁词但是日常表达,不应触发拦截
EXTREME_WORD_WHITELIST_PHRASES = [
    # 「第一」类（序数 + 量词组合都是正常用法，非广告法极限词）
    "第一反应", "第一感觉", "第一时间", "第一次", "第一眼", "第一口", "第一印象",
    "第一视角", "第一人称", "第一段", "第一天",
    "第一件", "第一个", "第一步", "第一遍", "第一秒", "第一分钟",
    "第一行", "第一列", "第一周", "第一季", "第一回", "第一波", "第一批",
    # 「最」类
    "最近", "最后", "最初", "最终", "最多", "最少", "最先",
    "最值得", "最起码", "最不",
    # 「特效」类（视频/镜头特效，非医疗特效）
    "动图特效", "视觉特效", "镜头特效", "脸部特效", "滤镜特效", "字幕特效",
    # 「极致」类（形容程度，非广告极致）
    "调到了极致", "调到极致", "做到极致", "推到极致", "冷到极致", "热到极致",
    # 品牌内容反例
    "其他没了",  # 简爱品牌名内容,但是用于反例时常出现
]

# 不参与扫描的字段：合规元数据、reasoning_check 自检字段等。这些写的是反向提醒
# 「严禁出现 X」/「确认没有 X」之类，命中只是字面匹配，并非真违规。
EXCLUDED_FIELD_PREFIXES = (
    "compliance_notes",
    "compliance_specific_to_this_creator",
    "compliance_report",
    "reasoning_check",
    "script_id",
    "blogger_id",
    "creator.id",
    "meta",
    "generated_at",
    "platform",
)


def scan_extreme_words(
    script: dict[str, Any], 
    forbidden: dict[str, list[str]]
) -> list[dict[str, str]]:
    """扫描脚本所有文本字段,返回命中列表。"""
    hits = []
    
    # 提取所有需要扫描的文本字段
    text_fields = collect_text_fields(script)
    
    # 极限词类别(全部命中即拦截)
    hard_categories = [
        "extreme_words",
        "medical_claims", 
        "weight_loss_claims",
        "glucose_claims",
        "false_promises",
        "platform_forbidden",
        "category_specific",
        "brand_specific",
    ]
    
    for category in hard_categories:
        for word in forbidden.get(category, []):
            for field_name, field_text in text_fields.items():
                if word not in field_text:
                    continue
                
                # 检查是否所有出现都被白名单短语包含
                # 找到所有出现位置
                start = 0
                real_hits = []
                while True:
                    idx = field_text.find(word, start)
                    if idx < 0:
                        break
                    # 检查这个位置是否被某个白名单短语覆盖
                    in_whitelist = False
                    for phrase in EXTREME_WORD_WHITELIST_PHRASES:
                        if word not in phrase:
                            continue
                        # 在 field_text 中搜索 phrase,看是否覆盖到 idx 位置
                        phrase_start = field_text.find(phrase)
                        while phrase_start >= 0:
                            if phrase_start <= idx < phrase_start + len(phrase):
                                in_whitelist = True
                                break
                            phrase_start = field_text.find(phrase, phrase_start + 1)
                        if in_whitelist:
                            break
                    if not in_whitelist:
                        real_hits.append(idx)
                    start = idx + len(word)
                
                if real_hits:
                    # 用第一个真实命中来报告
                    hits.append({
                        "word": word,
                        "category": category,
                        "field": field_name,
                        "context": extract_context(field_text, word, window=15),
                        "suggestion": get_replacement_suggestion(word, category),
                    })
    
    return hits


def collect_text_fields(script: dict[str, Any]) -> dict[str, str]:
    """递归提取脚本里所有 string 字段,返回 {field_path: text}。

    EXCLUDED_FIELD_PREFIXES 列出的字段（compliance_notes/reasoning_check 等）跳过。
    这些字段写的是反向提醒，扫到「严禁出现 X」会被字面匹配，但不是真违规。
    """
    result = {}

    def _excluded(path: str) -> bool:
        for prefix in EXCLUDED_FIELD_PREFIXES:
            if path == prefix or path.startswith(prefix + ".") or path.startswith(prefix + "["):
                return True
        return False

    def walk(node, path):
        if isinstance(node, str):
            if node.strip() and not _excluded(path):
                result[path] = node
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)

    walk(script, "")
    return result


def extract_context(text: str, word: str, window: int = 15) -> str:
    """提取命中词的上下文片段。"""
    idx = text.find(word)
    if idx < 0:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(word) + window)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def get_replacement_suggestion(word: str, category: str) -> str:
    """根据违禁词类别给出替换建议。"""
    suggestions = {
        "extreme_words": f"删除「{word}」或替换为相对化表述",
        "medical_claims": f"删除「{word}」,食品不能宣称医疗效果",
        "weight_loss_claims": f"删除「{word}」,转用场景化表达(如「适合早餐」「比较扛饿」)",
        "glucose_claims": f"删除「{word}」,可保留「0 蔗糖」配方描述但不能延伸到功效",
        "false_promises": f"删除「{word}」,使用相对化、具体化表述",
        "platform_forbidden": f"删除「{word}」,小红书平台敏感词",
        "category_specific": f"删除或软化「{word}」,见 forbidden_words.md 软化措辞建议",
        "brand_specific": f"删除「{word}」,与品牌长期定位冲突",
    }
    return suggestions.get(category, f"删除或替换「{word}」")


# -------- 医疗/减肥承诺隐性检测 --------

# 这一层用规则引擎做模式匹配,捕捉「字面没用违禁词但语境违规」的情况
IMPLICIT_PATTERNS = [
    {
        "pattern": r"(吃|喝|用)了.{0,10}(就|后).{0,15}(瘦|轻|小|窄|细)",
        "issue": "暗示「吃了 X 就瘦了」式因果",
    },
    {
        "pattern": r"替代.{0,5}(正餐|主食|晚餐|早饭)",
        "issue": "暗示替代正餐(代餐宣称需要保健食品资质)",
    },
    {
        "pattern": r"(比|跟).{0,15}(米饭|面条|主食|奶茶).{0,10}(瘦|低卡|不胖)",
        "issue": "比较类暗示减肥效果",
    },
    {
        "pattern": r"补充.{0,5}蛋白质",
        "issue": "「补充蛋白质」是功能性宣称,可改为「早上有蛋白质垫底」",
    },
    {
        "pattern": r"增肌",
        "issue": "「增肌」是功能性宣称,普通食品不能用",
    },
    {
        "pattern": r"控糖.{0,3}效果",
        "issue": "「控糖效果」是功效宣称,违规",
    },
    {
        "pattern": r"\d+\s*(斤|kg|公斤).{0,15}(瘦|减|轻)",
        "issue": "具体减重数字暗示减肥承诺",
    },
    {
        "pattern": r"BMI",
        "issue": "BMI 提及容易引发身材焦虑/极端瘦身联想",
    },
]


def detect_implicit_violations(script: dict[str, Any]) -> list[dict[str, str]]:
    """检测字面合规但语境违规的情况。"""
    hits = []
    text_fields = collect_text_fields(script)
    
    for pattern_def in IMPLICIT_PATTERNS:
        pattern = re.compile(pattern_def["pattern"])
        for field_name, field_text in text_fields.items():
            for match in pattern.finditer(field_text):
                hits.append({
                    "issue": pattern_def["issue"],
                    "matched_text": match.group(0),
                    "field": field_name,
                })
    
    return hits


# -------- LLM-as-Judge(可选)--------

def llm_judge_optional(
    script: dict[str, Any],
    blogger_profile_path: str | None = None,
    api_key: str | None = None,
) -> dict[str, int] | None:
    """
    用 Claude 对脚本做整体审查,给三个维度打分(1-10):
    - overall_compliance: 整体合规度
    - creator_style_similarity: 与博主风格的相似度
    - naturalness: 自然度(像不像真人写的)
    
    需要 ANTHROPIC_API_KEY 环境变量。如果未设置,返回 None。
    """
    import os
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    
    try:
        import anthropic
    except ImportError:
        print("⚠️  未安装 anthropic 包,跳过 LLM 审查。pip install anthropic 启用此功能", file=sys.stderr)
        return None
    
    client = anthropic.Anthropic(api_key=api_key)
    
    blogger_context = ""
    if blogger_profile_path and Path(blogger_profile_path).exists():
        blogger_context = Path(blogger_profile_path).read_text(encoding="utf-8")[:3000]
    
    prompt = f"""你是小红书蒲公英平台的报备审核员,同时是一位有 5 年经验的 MCN 内容策划。

请对下面这条小红书短视频脚本做三维度评分(每个维度 1-10):

**评分维度**:
1. overall_compliance(整体合规度): 是否暗示减肥/降糖/治疗/极端瘦身,广告法风险有多大
2. creator_style_similarity(博主风格相似度): 跟博主原本调性的相似程度,有没有写得像通用商业文案
3. naturalness(自然度): 像不像真人写的,有没有 AI 生硬感

**博主风格档案**(参考):
{blogger_context if blogger_context else "(未提供)"}

**待审脚本**:
```json
{json.dumps(script, ensure_ascii=False, indent=2)[:5000]}
```

请只返回 JSON 格式的评分结果,不要其他文字:
{{"overall_compliance": <int>, "creator_style_similarity": <int>, "naturalness": <int>, "rationale": "<一句话说明扣分原因>"}}
"""
    
    try:
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL_JUDGE", "claude-haiku-4-5-20251001"),
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # 去除可能的 markdown 代码块标记
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️  LLM 审查失败: {e}", file=sys.stderr)
        return None


# -------- 结构化硬约束检查(植入比例 / 品牌名连读 / 标题指向产品)--------

# 标题指向产品的代词模式
TITLE_PRODUCT_POINTER_PATTERNS = [
    r"这[一]?勺",
    r"这[一]?杯",
    r"这[一]?罐",
    r"这[一]?盒",
    r"这[一]?瓶",
    r"这[一]?款",
    r"就靠这",
    r"全靠这",
    r"靠它",
]

# 品牌名 + 产品类目连读模式(动态生成,基于 brand 和 category)
def build_brand_full_name_patterns(brand: str = "轻醒") -> list[str]:
    """构造品牌+品类连读的违规模式。"""
    categories = ["酸奶", "希腊酸奶", "高蛋白酸奶", "0蔗糖酸奶", "0 蔗糖酸奶"]
    return [f"{brand}{cat}" for cat in categories] + [f"{brand} {cat}" for cat in categories]


def check_structural_constraints(script: dict) -> list[dict]:
    """
    结构化硬约束检查:
    1. 植入段(segment_type=core_delivery)总时长是否 ≤30 秒
    2. 总时长是否在 60-90 秒之间
    3. 标题是否包含指向产品的代词
    4. 口播是否出现「品牌名+品类」连读
    5. 非广段是否照搬原参考笔记的具体场景
    """
    hits = []
    
    # 1. 植入时长检查 - 遍历 body 数组,累计 segment_type=core_delivery 的时长
    body = script.get("body", [])
    core_delivery_duration = 0
    
    # 关键词标记 body 里属于「结尾回扣」的 core_delivery 段——这些段已经
    # 通过顶层 ending_callback 字段表达，不再算进植入时长，避免双计触发误拦。
    _CALLBACK_LABEL_KEYWORDS = ("结尾回扣", "回扣", "callback", "ending")
    for segment in body:
        if segment.get("segment_type") != "core_delivery":
            continue
        label = segment.get("segment_label", "")
        is_callback_in_body = any(kw in label for kw in _CALLBACK_LABEL_KEYWORDS)
        if is_callback_in_body:
            continue  # 跟顶层 ending_callback 同义，跳过避免双计
        timestamp = segment.get("timestamp", "")
        match = re.match(r"(\d+)-(\d+)s?", timestamp)
        if match:
            core_delivery_duration += int(match.group(2)) - int(match.group(1))

    # 顶层 ending_callback 默认 +5 秒
    callback = script.get("ending_callback", {})
    if callback and callback.get("voiceover"):
        core_delivery_duration += 5
    
    # 也支持顶级字段(向后兼容)
    explicit_product_dur = script.get("product_segment_duration_seconds")
    if isinstance(explicit_product_dur, (int, float)) and explicit_product_dur > core_delivery_duration:
        core_delivery_duration = explicit_product_dur
    
    if core_delivery_duration > 30:
        hits.append({
            "constraint": "product_segment_duration_cap",
            "issue": f"产品植入段(core_delivery)总时长 {core_delivery_duration} 秒超过 30 秒上限",
            "field": "body[segment_type=core_delivery]",
            "suggestion": "压缩 core_delivery 段落到 ≤30 秒,把时长用于 reference_only 的非广段补全",
        })
    
    # 2. 总时长检查
    total_duration = script.get("duration_seconds")
    if isinstance(total_duration, (int, float)):
        if total_duration < 60 or total_duration > 90:
            hits.append({
                "constraint": "total_duration_range",
                "issue": f"总时长 {total_duration} 秒不在 60-90 秒区间内",
                "field": "duration_seconds",
                "suggestion": "调整非广段时长,使总时长落在 60-90 秒之间",
            })
    
    # 3. 标题指向产品检查
    title = script.get("title", "")
    for pattern in TITLE_PRODUCT_POINTER_PATTERNS:
        if re.search(pattern, title):
            hits.append({
                "constraint": "title_product_pointer",
                "issue": f"标题包含指向产品的代词「{pattern}」,会被识别为硬广",
                "field": "title",
                "matched": title,
                "suggestion": "标题改为指向场景/状态/情绪,不指向具体产品",
            })
    
    # 4. 品牌名连读检查
    brand = script.get("brand", "轻醒")
    brand_full_patterns = build_brand_full_name_patterns(brand)
    
    text_fields = collect_text_fields(script)
    voiceover_fields = {
        k: v for k, v in text_fields.items()
        if any(token in k.lower() for token in ["voiceover", "transition_line", "口播"])
    }
    
    for field_name, field_text in voiceover_fields.items():
        for pattern in brand_full_patterns:
            if pattern in field_text:
                hits.append({
                    "constraint": "brand_full_name_in_voiceover",
                    "issue": f"口播中出现品牌+品类全称连读「{pattern}」,广告感强",
                    "field": field_name,
                    "context": extract_context(field_text, pattern, window=15),
                    "suggestion": f"改为「这个酸奶」「叫{brand}」「这罐子」等替代指称",
                })
    
    # 5. 非广段照搬检查
    forbidden_scenes = {
        "catherine_xiaoxiong": [
            "脑爆材料", "左右脑互搏", "魔大食堂", "厚切三文鱼", 
            "泰式按摩", "香香软软", "欧阳春晓", "天鹅湖",
        ],
        "couhuohuo": [
            "米露", "揉米", "韩料店", "冷冻麻辣烫", "家乐", 
            "星露谷", "煤矿森林", "野葱", "水晶手串", "装大象一样",
        ],
    }
    
    creator_id = script.get("creator", {}).get("id", "")
    if creator_id in forbidden_scenes:
        for segment in body:
            if segment.get("segment_type") != "reference_only":
                continue
            seg_text = (
                segment.get("voiceover", "") + " " +
                segment.get("shot_description", "") + " " +
                segment.get("based_on_palette_item", "")
            )
            for forbidden_scene in forbidden_scenes[creator_id]:
                if forbidden_scene in seg_text:
                    hits.append({
                        "constraint": "non_ad_content_copying",
                        "issue": f"非广段直接复用了原参考笔记的具体场景「{forbidden_scene}」",
                        "field": f"body[segment_type=reference_only]",
                        "suggestion": f"改用博主档案 non_ad_content_palette 里的新场景,不要抄原笔记",
                    })
    
    # 6. 工位场景红线检查(NDA / 劳动法风险)
    # 适用于 Catherine 等工位类博主
    workplace_bloggers = ["catherine_xiaoxiong"]
    
    if creator_id in workplace_bloggers:
        workplace_red_flags = [
            # 屏幕内容相关
            ("工位屏幕", "工位屏幕显示具体内容(NDA 风险),只能拍键盘/手部/咖啡杯/楼道,屏幕需虚化或不入镜"),
            ("屏幕特写", "屏幕特写可能显示具体业务,改为模糊背景或拍其他物品"),
            ("屏幕上", "拍摄屏幕上的具体内容触及 NDA"),
            ("屏幕反光", "屏幕反光可能暴露具体内容"),
            # 公司/客户/项目可识别信息
            ("具体公司", "拍摄公司名 / logo 触及 NDA"),
            ("公司名", "公司名不能出现"),
            ("logo", "公司 logo 不能出现"),
            ("工牌", "工牌触及 NDA"),
            ("门禁", "门禁卡可能显示公司信息"),
            # 业务可识别内容
            ("代码", "拍代码内容触及 NDA"),
            ("具体客户", "客户名/客户内容触及 NDA"),
            ("KPI", "真实 KPI 数字触及保密"),
            ("PPT 内容", "PPT 内容可能显示具体业务,改为模糊背景"),
            ("文档内容", "文档内容触及 NDA"),
            ("邮件内容", "邮件内容触及 NDA"),
            ("聊天记录", "聊天记录触及隐私和 NDA"),
            # 同事可识别
            ("同事的脸", "拍摄同事容貌侵犯肖像权"),
            ("同事正脸", "同事正脸不能出现"),
            ("领导", "拍摄领导可能涉及肖像权和 NDA"),
        ]
        
        # 良性「屏幕」类复合词：手机屏幕道具、模糊屏幕背景等不是真业务暴露。
        # 关键：白名单短语必须**完整包含**红线关键词（如「手机屏幕上」覆盖「屏幕上」），
        # 否则在 desc 里同一 idx 的 keyword 命中不会被豁免。
        nda_safe_phrases = (
            # 「屏幕上」的良性场景：手机道具 / 屏幕上方字幕区 / 模糊背景上的字幕
            "手机屏幕上", "屏幕上方", "屏幕上半部",
            # 「屏幕特写」「屏幕反光」的良性场景（罕见，但 cover 一下）
            "手机屏幕特写", "手机屏幕反光",
            # 「屏幕」单独类的良性场景（这些不是 keyword 但放着以防扩展）
            "模糊屏幕背景", "屏幕背景模糊",
        )

        def _is_in_safe_phrase(desc, kw_idx, kw):
            for safe in nda_safe_phrases:
                if kw not in safe:
                    continue
                start = 0
                while True:
                    p = desc.find(safe, start)
                    if p < 0:
                        break
                    if p <= kw_idx < p + len(safe):
                        return True
                    start = p + 1
            return False

        for segment in body:
            shot_desc = segment.get("shot_description", "")
            for keyword, issue in workplace_red_flags:
                idx = shot_desc.find(keyword)
                if idx < 0:
                    continue
                # 过滤：命中位置是否被良性短语覆盖（手机屏幕/模糊屏幕等）
                if _is_in_safe_phrase(shot_desc, idx, keyword):
                    continue
                # 真违规
                hits.append({
                    "constraint": "workplace_nda_risk",
                    "issue": f"画面描述含「{keyword}」: {issue}",
                    "field": f"body[timestamp={segment.get('timestamp', '?')}].shot_description",
                    "context": shot_desc[:80],
                    "suggestion": "改为「键盘/鼠标/手部特写」「咖啡杯/绿植/工位摆件」「办公楼大堂/楼道」「模糊屏幕背景」等安全场景",
                })
                break  # 一段画面命中一次就够
    
    return hits


# -------- 主入口 --------

def check_script(
    script: dict[str, Any],
    forbidden_words_path: str = "references/forbidden_words.md",
    blogger_profile_path: str | None = None,
    enable_llm_judge: bool = False,
) -> dict[str, Any]:
    """
    执行完整 4 层质检,返回 compliance_report。
    
    返回字段:
        compliance_status: "通过" | "警告" | "拦截"
        extreme_words_hits: list[...]
        medical_implication_hits: list[...]
        structural_constraint_hits: list[...]  # 新增
        llm_judge_score: dict | None
        recommendations: list[str]
    """
    # 第 1 层: 极限词扫描
    forbidden = load_forbidden_words(forbidden_words_path)
    extreme_hits = scan_extreme_words(script, forbidden)
    
    # 第 2 层: 隐性违规检测
    implicit_hits = detect_implicit_violations(script)
    
    # 第 3 层: 结构化硬约束检查(植入时长/标题/品牌名连读)
    structural_hits = check_structural_constraints(script)
    
    # 第 4 层: LLM-as-Judge(可选)
    llm_score = None
    if enable_llm_judge:
        llm_score = llm_judge_optional(script, blogger_profile_path)
    
    # 决定最终状态
    status = "通过"
    recommendations = []
    
    # 拦截规则
    if len(extreme_hits) >= 1:
        status = "拦截"
        recommendations.append(f"命中 {len(extreme_hits)} 个广告法/医疗/减肥违禁词,必须删除或替换后重新生成")
    
    if len(implicit_hits) >= 1:
        if len(implicit_hits) >= 2:
            status = "拦截"
        else:
            status = "警告" if status == "通过" else status
        recommendations.append(f"发现 {len(implicit_hits)} 处隐性违规(字面合规但语境违规),建议修改")
    
    if len(structural_hits) >= 1:
        # 结构化约束违反默认拦截 - 这些是 MCN 业务硬规则
        status = "拦截"
        recommendations.append(
            f"发现 {len(structural_hits)} 处 MCN 业务规则违规("
            + ", ".join(set(h["constraint"] for h in structural_hits))
            + "),必须修改"
        )
    
    if llm_score:
        for dim, score in llm_score.items():
            if not isinstance(score, int):
                continue
            if score < 4:
                status = "拦截"
                recommendations.append(f"LLM 审查 {dim} 仅 {score}/10,需重新生成")
            elif score < 6:
                status = "警告" if status == "通过" else status
                recommendations.append(f"LLM 审查 {dim} 仅 {score}/10,建议人工 review")
    
    if status == "通过":
        recommendations.append("脚本通过 4 层质检,可以提交给博主拍摄")
    
    return {
        "compliance_status": status,
        "extreme_words_hits": extreme_hits,
        "medical_implication_hits": implicit_hits,
        "structural_constraint_hits": structural_hits,
        "llm_judge_score": llm_score,
        "recommendations": recommendations,
    }


def main():
    parser = argparse.ArgumentParser(description="MCN 脚本风险质检")
    parser.add_argument("--script", required=True, help="脚本 JSON 文件路径")
    parser.add_argument("--forbidden", default="references/forbidden_words.md", help="违禁词库路径")
    parser.add_argument("--blogger-profile", default=None, help="博主档案路径(LLM 审查用)")
    parser.add_argument("--output", default=None, help="输出报告路径,不指定则打印到 stdout")
    parser.add_argument("--llm-judge", action="store_true", help="启用 LLM-as-Judge(需要 ANTHROPIC_API_KEY)")
    
    args = parser.parse_args()
    
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    report = check_script(
        script,
        forbidden_words_path=args.forbidden,
        blogger_profile_path=args.blogger_profile,
        enable_llm_judge=args.llm_judge,
    )
    
    output_text = json.dumps(report, ensure_ascii=False, indent=2)
    
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"✓ 质检报告已写入 {args.output}")
        print(f"  状态: {report['compliance_status']}")
        print(f"  极限词命中: {len(report['extreme_words_hits'])} 个")
        print(f"  隐性违规: {len(report['medical_implication_hits'])} 处")
    else:
        print(output_text)
    
    # 退出码: 通过=0, 警告=1, 拦截=2
    return {"通过": 0, "警告": 1, "拦截": 2}.get(report["compliance_status"], 1)


if __name__ == "__main__":
    sys.exit(main())
