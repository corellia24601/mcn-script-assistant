"""Coze 工作流代码节点：把 LLM 输出的脚本 JSON 转成飞书多维表格 records 数组。

Coze 代码节点入参：args（dict-like），含字段 `scripts`（JSON 字符串或数组）。
输出：dict，含字段 `records`（list，可直接喂给飞书 batch_create）。

写在仓库内方便版本控制；粘到 Coze 时只复制 `main` 函数体即可。
依赖：Coze 内建 Python 运行时仅 stdlib，本文件不引外部库。
"""
from __future__ import annotations

import json
from typing import Any

# 飞书表头与脚本字段的映射。改字段时只动这里。
FIELD_MAP: dict[str, str] = {
    "blogger_id": "博主 ID",
    "script_id": "脚本编号",
    "video_length_sec": "时长(秒)",
    "hook_text": "钩子文案",
    "scenes_summary": "分镜概要",
    "cta": "行动召唤",
    "tags": "Tag",
    "risk_summary": "风险概览",
    "model": "生成模型",
    "generated_at": "生成时间",
}


def _scripts_to_record(script: dict[str, Any]) -> dict[str, Any]:
    scenes = script.get("scenes") or []
    scenes_summary = " | ".join(
        f"{s.get('order')}.{s.get('voiceover', '')[:30]}" for s in scenes
    )
    risk_flags = script.get("risk_flags") or []
    if not risk_flags:
        risk_summary = "无命中"
    else:
        levels = [f["level"] for f in risk_flags]
        h = levels.count("H")
        m = levels.count("M")
        l = levels.count("L")
        risk_summary = f"H={h} M={m} L={l}"
    meta = script.get("meta") or {}
    return {
        FIELD_MAP["blogger_id"]: script.get("blogger_id", ""),
        FIELD_MAP["script_id"]: script.get("script_id", ""),
        FIELD_MAP["video_length_sec"]: script.get("video_length_sec", 0),
        FIELD_MAP["hook_text"]: (script.get("hook") or {}).get("text", ""),
        FIELD_MAP["scenes_summary"]: scenes_summary,
        FIELD_MAP["cta"]: script.get("cta", ""),
        FIELD_MAP["tags"]: ", ".join(script.get("tags") or []),
        FIELD_MAP["risk_summary"]: risk_summary,
        FIELD_MAP["model"]: meta.get("model", ""),
        FIELD_MAP["generated_at"]: meta.get("generated_at", ""),
    }


def main(args: dict[str, Any]) -> dict[str, Any]:
    payload = args.get("scripts")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"unexpected scripts payload type: {type(payload).__name__}")
    records = [{"fields": _scripts_to_record(s)} for s in payload]
    return {"records": records, "count": len(records)}


# 本地自测
if __name__ == "__main__":  # pragma: no cover
    sample = {
        "blogger_id": "xx-001",
        "script_id": "qx-test-01",
        "video_length_sec": 60,
        "hook": {"text": "下午三点又开始馋甜的？"},
        "scenes": [
            {"order": 1, "voiceover": "我最近嘴馋的时候会先翻冰箱"},
            {"order": 2, "voiceover": "口感比想象中扎实"},
        ],
        "cta": "评论区聊聊你的下午茶搭配",
        "tags": ["希腊酸奶", "下午茶"],
        "risk_flags": [],
        "meta": {"model": "deepseek-chat", "generated_at": "2026-04-30T12:00:00Z"},
    }
    print(json.dumps(main({"scripts": [sample]}), ensure_ascii=False, indent=2))
