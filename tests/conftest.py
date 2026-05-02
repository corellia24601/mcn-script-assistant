"""pytest fixtures：脚本/规则/飞书 mock。"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# scripts 目录因含连字符无法做包，强制加进 sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "mcn-script-assistant" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def forbidden_words_path() -> Path:
    return REPO_ROOT / "skills" / "mcn-script-assistant" / "references" / "forbidden_words.md"


@pytest.fixture
def sample_script_dict() -> dict:
    """一个干净（无违禁词）的脚本字典，复用为多种测试场景的基底。"""
    return {
        "blogger_id": "xx-001",
        "script_id": "qx-test-01",
        "platform": "xiaohongshu",
        "video_length_sec": 60,
        "hook": {
            "text": "下午三点又开始馋甜的？",
            "visual": "办公桌上摊开的零食袋",
            "type": "scene",
        },
        "scenes": [
            {
                "order": 1,
                "duration_sec": 20,
                "scene": "镜头特写打开希腊酸奶杯",
                "voiceover": "我最近嘴馋的时候会先翻冰箱",
                "on_screen_text": "下午茶替代清单",
            },
            {
                "order": 2,
                "duration_sec": 20,
                "scene": "把酸奶倒进玻璃碗",
                "voiceover": "口感比想象中扎实",
                "on_screen_text": "",
            },
            {
                "order": 3,
                "duration_sec": 20,
                "scene": "撒一点水果",
                "voiceover": "搭配下午茶刚好",
                "on_screen_text": "你也试试",
            },
        ],
        "cta": "评论区聊聊你的下午茶搭配",
        "tags": ["希腊酸奶", "下午茶", "高蛋白", "办公室零食", "夏日饮食"],
        "risk_flags": [],
        "meta": {
            "model": "deepseek-chat",
            "skill_version": "0.1.0",
            "generated_at": "2026-04-30T12:00:00Z",
            "brief_version": "qx-2026Q2-test",
        },
    }
