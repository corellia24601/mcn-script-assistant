"""违禁词扫描相关测试 —— 适配 SKILL.md Step 5 的 dict-based check_script API。

旧版基于 Pydantic Schema 的测试已废弃；本文件测试的是
skills/mcn-script-assistant/scripts/risk_check.py 中：
- load_forbidden_words：解析 forbidden_words.md 的 yaml 块
- scan_extreme_words：扫描脚本所有文本字段
- detect_implicit_violations：隐性违规正则
- check_script：三层质检整合，返回 compliance_report
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from risk_check import (
    check_script,
    collect_text_fields,
    detect_implicit_violations,
    extract_context,
    load_forbidden_words,
    scan_extreme_words,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_PATH = REPO_ROOT / "skills" / "mcn-script-assistant" / "references" / "forbidden_words.md"


# ---------- fixtures ----------


@pytest.fixture
def forbidden() -> dict[str, list[str]]:
    return load_forbidden_words(str(FORBIDDEN_PATH))


@pytest.fixture
def clean_script() -> dict:
    """无违禁词的最简脚本，用于做反例。"""
    return {
        "script_id": "test-01",
        "brand": "轻醒",
        "creator": {"id": "catherine_xiaoxiong", "display_name": "Catherine是小熊"},
        "title": "周一也清爽松软",
        "duration_seconds": 75,
        "hook": {
            "duration_seconds": "0-5 秒",
            "shots": ["走路仰拍", "工位特写", "fit check"],
            "voiceover_first_line": "写脑爆材料的早起日穿什么",
            "bgm_note": "网络热门 BGM",
        },
        "body": [
            {
                "timestamp": "5-15s",
                "segment_label": "起床段",
                "voiceover": "嘴馋的时候先翻冰箱",
                "shot_description": "镜头特写打开希腊酸奶杯",
            },
        ],
        "product_insertion": {
            "at_second": "15-45s",
            "transition_line": "我现在要垫一勺",
            "package_close_up_duration": "2-3 秒",
            "sensory_description": "黄桃丁咬到的瞬间像周二突然变成周五",
            "action_shots": ["挖一勺立着不滴", "镜头拉近"],
            "callback_at_ending": "下午三点居然没饿",
        },
        "cta": {"style": "戏剧化感受式", "voiceover": "不会是睡美人吧"},
        "compliance_notes": ["注意软化措辞"],
    }


# ---------- load_forbidden_words ----------


def test_load_real_file_yields_known_words(forbidden):
    # 必须包含 brief 红线
    assert "减肥" in forbidden["weight_loss_claims"]
    assert "降糖" in forbidden["glucose_claims"]
    assert "100%" in forbidden["extreme_words"]
    assert "治疗" in forbidden["medical_claims"]
    # 软化建议块不混入主词表
    assert "效果" not in forbidden["extreme_words"]


def test_load_skips_softening_and_caution_blocks(tmp_path):
    md = tmp_path / "f.md"
    md.write_text(
        "## A\n```yaml\nextreme_words:\n  - 最\n  - 第一\n```\n"
        "## B\n```yaml\nsoftening_suggestions:\n  \"效果\":\n    use: \"感受\"\n```\n"
        "## C\n```yaml\ncaution_zone:\n  \"饱腹感\":\n    rule: \"必须配软化\"\n```\n",
        encoding="utf-8",
    )
    rules = load_forbidden_words(str(md))
    assert rules["extreme_words"] == ["最", "第一"]
    # softening / caution 不应进入任何类目
    for cat in rules.values():
        assert "效果" not in cat
        assert "饱腹感" not in cat


# ---------- collect_text_fields / extract_context ----------


def test_collect_text_fields_walks_nested(clean_script):
    fields = collect_text_fields(clean_script)
    # hook.shots[0] 应该是嵌套路径
    assert any(k.startswith("hook.shots[") for k in fields)
    # 空字符串应被跳过
    assert all(v.strip() for v in fields.values())


def test_extract_context_clips_around_word():
    s = "abcdefghijklmnopqrstuvwxyz" + "减肥" + "abcdefghijklmnopqrstuvwxyz"
    ctx = extract_context(s, "减肥", window=5)
    assert "减肥" in ctx
    assert ctx.startswith("...") and ctx.endswith("...")


# ---------- scan_extreme_words ----------


def test_scan_clean_script_no_hits(clean_script, forbidden):
    hits = scan_extreme_words(clean_script, forbidden)
    assert hits == []


def test_scan_catches_advertising_extreme_words(clean_script, forbidden):
    s = dict(clean_script)
    s["title"] = "全网最好的酸奶"  # 命中「最」
    hits = scan_extreme_words(s, forbidden)
    matched = {h["word"] for h in hits}
    assert "最" in matched


def test_scan_catches_weight_loss_claims(clean_script, forbidden):
    s = dict(clean_script)
    s["cta"] = {"style": "戏剧化感受式", "voiceover": "再这样吃减肥就完了"}
    hits = scan_extreme_words(s, forbidden)
    assert any(h["word"] == "减肥" for h in hits)


def test_scan_catches_glucose_claims(clean_script, forbidden):
    s = dict(clean_script)
    s["product_insertion"] = dict(clean_script["product_insertion"])
    s["product_insertion"]["sensory_description"] = "降糖效果一流"
    hits = scan_extreme_words(s, forbidden)
    matched = {h["word"] for h in hits}
    # 应至少命中「降糖」
    assert "降糖" in matched


def test_scan_returns_field_path_and_suggestion(clean_script, forbidden):
    s = dict(clean_script)
    s["title"] = "100% 唯一的酸奶"
    hits = scan_extreme_words(s, forbidden)
    for h in hits:
        assert "field" in h and h["field"]
        assert "suggestion" in h and h["suggestion"]


# ---------- detect_implicit_violations ----------


def test_implicit_protein_supplement_caught(clean_script):
    s = dict(clean_script)
    s["product_insertion"] = dict(clean_script["product_insertion"])
    s["product_insertion"]["sensory_description"] = "早上补充蛋白质很方便"
    hits = detect_implicit_violations(s)
    assert any("蛋白质" in h["matched_text"] for h in hits)


def test_implicit_replace_meal_caught(clean_script):
    s = dict(clean_script)
    s["body"] = [
        {
            "timestamp": "5-15s",
            "segment_label": "x",
            "voiceover": "用它替代正餐刚刚好",
            "shot_description": "x",
        }
    ]
    hits = detect_implicit_violations(s)
    assert any("替代" in h["matched_text"] for h in hits)


def test_implicit_bmi_caught(clean_script):
    s = dict(clean_script)
    s["title"] = "BMI 17 吃什么"
    hits = detect_implicit_violations(s)
    assert any("BMI" in h["matched_text"] for h in hits)


def test_implicit_no_false_positive_on_clean(clean_script):
    assert detect_implicit_violations(clean_script) == []


# ---------- check_script 整合 ----------


def test_check_script_clean_passes(clean_script):
    report = check_script(clean_script, forbidden_words_path=str(FORBIDDEN_PATH))
    assert report["compliance_status"] == "通过"
    assert report["extreme_words_hits"] == []
    assert report["medical_implication_hits"] == []
    assert report["llm_judge_score"] is None


def test_check_script_extreme_word_intercepts(clean_script):
    s = dict(clean_script)
    s["title"] = "全网最好的酸奶"
    report = check_script(s, forbidden_words_path=str(FORBIDDEN_PATH))
    assert report["compliance_status"] == "拦截"
    assert any(h["word"] == "最" for h in report["extreme_words_hits"])


def test_check_script_two_implicit_promotes_to_intercept(clean_script):
    s = dict(clean_script)
    s["body"] = [
        {
            "timestamp": "5-15s",
            "segment_label": "x",
            "voiceover": "替代正餐刚刚好",
            "shot_description": "x",
        }
    ]
    s["cta"] = {"style": "戏剧化感受式", "voiceover": "补充蛋白质很方便"}
    report = check_script(s, forbidden_words_path=str(FORBIDDEN_PATH))
    # 两条隐性违规应升级为拦截
    assert report["compliance_status"] == "拦截"
    assert len(report["medical_implication_hits"]) >= 2


def test_check_script_single_implicit_warns(clean_script):
    s = dict(clean_script)
    s["cta"] = {"style": "戏剧化感受式", "voiceover": "补充蛋白质很方便"}
    report = check_script(s, forbidden_words_path=str(FORBIDDEN_PATH))
    assert report["compliance_status"] == "警告"


def test_check_script_llm_judge_low_score_intercepts(clean_script):
    fake_score = {
        "overall_compliance": 8,
        "creator_style_similarity": 3,  # < 4 → 拦截
        "naturalness": 7,
    }
    with patch("risk_check.llm_judge_optional", return_value=fake_score):
        report = check_script(
            clean_script,
            forbidden_words_path=str(FORBIDDEN_PATH),
            enable_llm_judge=True,
        )
    assert report["compliance_status"] == "拦截"
    assert report["llm_judge_score"] == fake_score


def test_check_script_llm_judge_mid_score_warns(clean_script):
    fake_score = {
        "overall_compliance": 5,  # 4-5 → 警告
        "creator_style_similarity": 7,
        "naturalness": 8,
    }
    with patch("risk_check.llm_judge_optional", return_value=fake_score):
        report = check_script(
            clean_script,
            forbidden_words_path=str(FORBIDDEN_PATH),
            enable_llm_judge=True,
        )
    assert report["compliance_status"] == "警告"
