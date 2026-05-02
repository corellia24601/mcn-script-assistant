"""
write_to_feishu.py - 把脚本写入飞书多维表格

被 SKILL.md 的 Step 6 调用。

使用前必须配置以下环境变量:
    FEISHU_APP_ID         - 飞书自建应用 ID
    FEISHU_APP_SECRET     - 飞书自建应用 Secret
    FEISHU_BITABLE_APP_TOKEN  - 多维表格 app_token(URL 中提取)
    FEISHU_BITABLE_TABLE_ID   - 表格 table_id(URL 中提取)

权限要求(在飞书开放平台 → 应用 → 权限管理):
    bitable:app          - 多维表格应用读写
    bitable:app:readonly - 多维表格应用只读(可选)
    
配置完权限后必须「发布版本」才生效(常见踩坑)。

用法:
    python write_to_feishu.py --script output/final_script.json
    
或作为模块导入:
    from write_to_feishu import write_script_to_bitable
    record_url = write_script_to_bitable(script_dict)
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("✗ 缺少依赖: pip install requests", file=sys.stderr)
    sys.exit(1)

# 启动时自动加载仓库根 .env
try:
    from dotenv import load_dotenv  # type: ignore
    _repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(_repo_root / ".env", override=False)
except ImportError:
    pass


FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


# -------- 鉴权 --------

def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token,有效期 2 小时。"""
    url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
    response = requests.post(
        url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"飞书鉴权失败: {data.get('msg')} (code={data.get('code')})")
    return data["tenant_access_token"]


# -------- 字段格式化 --------

# v3 schema 段落标签关键词，用于识别 body 里哪段是「开场钩子段」
_HOOK_LABEL_KEYWORDS = ("开场", "钩子", "hook", "opening", "起点", "起步")
_CALLBACK_LABEL_KEYWORDS = ("结尾回扣", "回扣", "callback", "ending")


def _find_hook_segment(body: list) -> dict | None:
    """从 body 数组里找开场钩子段。优先 segment_label 匹配，兜底用第一段。"""
    for seg in body:
        label = seg.get("segment_label", "")
        if any(kw in label for kw in _HOOK_LABEL_KEYWORDS):
            return seg
    return body[0] if body else None


def _is_callback_in_body(seg: dict) -> bool:
    label = seg.get("segment_label", "")
    return any(kw in label for kw in _CALLBACK_LABEL_KEYWORDS)


def _format_storyboard_readable(storyboard: list) -> str:
    """分镜表格式化为可读文本（不是 JSON），方便飞书表格里直接读。"""
    if not storyboard:
        return ""
    lines = []
    for shot in storyboard:
        shot_num = shot.get("shot_number", "?")
        dur = shot.get("duration_seconds", "?")
        seg_type = shot.get("segment_type", "")
        visual = shot.get("visual_description", "").strip()
        voice = shot.get("voiceover_or_subtitle", "").strip()
        props = shot.get("props_and_scene", "").strip()
        diff = shot.get("shooting_difficulty", "")
        lines.append(
            f"# 镜 {shot_num}（{dur}s · {seg_type} · 难度 {diff}）\n"
            f"  画面：{visual}\n"
            f"  口播/字幕：{voice}\n"
            f"  道具/场景：{props}"
        )
    return "\n\n".join(lines)


def _format_compliance_report(report: dict) -> str:
    """质检详情格式化为简明可读文本，不是 JSON。"""
    if not report:
        return "未质检"
    status = report.get("compliance_status", "?")
    parts = [f"状态：{status}"]

    extreme_hits = report.get("extreme_words_hits", []) or []
    implicit_hits = report.get("medical_implication_hits", []) or []
    structural_hits = report.get("structural_constraint_hits", []) or []

    if not (extreme_hits or implicit_hits or structural_hits):
        parts.append("（4 层质检全部通过：极限词扫描 + 隐性违规 + 结构约束 + LLM judge）")
    else:
        if extreme_hits:
            parts.append(f"极限词命中 {len(extreme_hits)} 处：")
            for h in extreme_hits[:5]:
                parts.append(f"  - 「{h.get('word','')}」@ {h.get('field','')}: {h.get('context','')[:40]}")
        if implicit_hits:
            parts.append(f"隐性违规 {len(implicit_hits)} 处：")
            for h in implicit_hits[:5]:
                parts.append(f"  - {h.get('issue','')} (匹配「{h.get('matched_text','')}」)")
        if structural_hits:
            parts.append(f"结构约束 {len(structural_hits)} 处：")
            for h in structural_hits[:5]:
                parts.append(f"  - [{h.get('constraint','')}] {h.get('issue','')}")

    recs = report.get("recommendations", []) or []
    if recs:
        parts.append("建议：")
        for r in recs[:5]:
            parts.append(f"  - {r}")
    return "\n".join(parts)


def _format_full_voiceover_v3(script: dict) -> str:
    """v3 schema：从 body[] + ending_callback 组装完整口播，按时间轴渲染。"""
    body = script.get("body", []) or []
    sections = []
    for seg in body:
        ts = seg.get("timestamp", "")
        seg_type = seg.get("segment_type", "")
        seg_label = seg.get("segment_label", "")
        voice = seg.get("voiceover", "").strip()
        type_tag = "🎯核心交付" if seg_type == "core_delivery" else "💡参考方向"
        head = f"[{ts}] {type_tag} · {seg_label}"
        sections.append(f"{head}\n{voice}")

    callback = script.get("ending_callback", {}) or {}
    cb_voice = callback.get("voiceover", "").strip()
    if cb_voice:
        sections.append(f"[结尾回扣 5s] 🎯核心交付\n{cb_voice}")

    return "\n\n".join(sections)


def _format_product_insertion_v3(script: dict) -> str:
    """v3 schema：产品植入点 = body 里 segment_type=core_delivery 且非结尾回扣的段落。"""
    body = script.get("body", []) or []
    parts = []
    for seg in body:
        if seg.get("segment_type") != "core_delivery":
            continue
        if _is_callback_in_body(seg):
            continue  # 结尾回扣单独成列
        ts = seg.get("timestamp", "")
        transition = seg.get("transition_line", "").strip()
        sensory = seg.get("sensory_description", "").strip()
        actions = seg.get("action_shots", []) or []
        voice = seg.get("voiceover", "").strip()
        block = [f"[{ts}] 产品植入段"]
        if transition:
            block.append(f"  过渡句：{transition}")
        if sensory:
            block.append(f"  感官描述：{sensory}")
        if actions:
            block.append(f"  关键动作镜头：{' / '.join(actions)}")
        if voice:
            block.append(f"  完整口播：{voice}")
        parts.append("\n".join(block))
    return "\n\n".join(parts)


def format_record_fields(script: dict[str, Any]) -> dict[str, Any]:
    """把脚本 JSON 映射成飞书多维表格的 fields 结构（v3 schema 适配）。

    评审硬要求：脚本必须包含 标题/钩子/口播/植入点/结尾CTA/合规提醒。
    本函数把这 6 项分别填入对应列。
    """
    body = script.get("body", []) or []

    # 钩子：从 body 里找开场段；优先 segment_label 含「开场/钩子/hook」，兜底 body[0]
    hook_seg = _find_hook_segment(body)
    hook_voice = (hook_seg or {}).get("voiceover", "").strip()

    # 完整口播：按时间轴拼所有 body 段 + ending_callback
    full_voiceover = _format_full_voiceover_v3(script)

    # 产品植入点：body 里 core_delivery 段（不含结尾回扣）的口播 + 过渡 + 感官 + 动作
    product_insertion = _format_product_insertion_v3(script)

    # 结尾 CTA 三级兜底：
    #   1) ending_callback.voiceover （Catherine 类有强回扣）
    #   2) script.cta.voiceover       （老 schema 兜底）
    #   3) body 最后一段的最后一句     （凑活活类「留白式收尾」博主，
    #      没有强 CTA，但 body 末尾的留白句就是她的软 CTA）
    callback = script.get("ending_callback") or {}
    cta_voice = callback.get("voiceover", "").strip()
    if not cta_voice:
        cta_voice = (script.get("cta", {}) or {}).get("voiceover", "").strip()
    if not cta_voice and body:
        last_voiceover = (body[-1].get("voiceover", "") or "").strip()
        # 按中文标点切句，取最后一句非空
        sentences = [s.strip() for s in re.split(r"[。！？!?]+", last_voiceover) if s.strip()]
        if sentences:
            cta_voice = f"（博主留白式收尾，无强回扣 CTA）{sentences[-1]}"

    # 合规风险提醒：compliance_notes 列表 join
    compliance_notes = script.get("compliance_notes", []) or []
    compliance_text = "\n".join(f"- {note}" for note in compliance_notes)

    # 分镜表：可读文本
    storyboard_text = _format_storyboard_readable(script.get("storyboard", []) or [])

    # 质检详情：简明摘要
    compliance_report = script.get("compliance_report", {}) or {}
    compliance_detail = _format_compliance_report(compliance_report)

    fields = {
        "脚本 ID": script.get("script_id", str(uuid.uuid4())[:8]),
        "品牌": script.get("brand", ""),
        "目标博主": (script.get("creator", {}) or {}).get("display_name", ""),
        "生成时间": int(datetime.now().timestamp() * 1000),
        "视频标题": script.get("title", ""),
        "开头钩子": hook_voice,
        "完整口播": full_voiceover,
        "产品植入点": product_insertion,
        "结尾CTA": cta_voice,
        "合规风险提醒": compliance_text,
        "分镜表": storyboard_text,
        "质检状态": compliance_report.get("compliance_status", "未质检"),
        "质检详情": compliance_detail,
        "备注": script.get("notes", ""),
    }
    return fields


# -------- 写入 --------

def write_record(
    app_token: str,
    table_id: str,
    fields: dict[str, Any],
    access_token: str,
) -> dict[str, Any]:
    """调用飞书 bitable API 写入一条记录。"""
    url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {"fields": fields}
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"飞书写入失败 HTTP {response.status_code}: {response.text}")
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"飞书业务错误 code={data.get('code')}: {data.get('msg')}\n"
            f"常见原因: 1)字段名不匹配 2)未发布应用版本 3)权限未开通"
        )
    return data["data"]["record"]


def write_script_to_bitable(
    script: dict[str, Any],
    app_id: str | None = None,
    app_secret: str | None = None,
    app_token: str | None = None,
    table_id: str | None = None,
) -> dict[str, Any]:
    app_id = app_id or os.environ.get("FEISHU_APP_ID")
    app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET")
    app_token = app_token or os.environ.get("FEISHU_BITABLE_APP_TOKEN")
    table_id = table_id or os.environ.get("FEISHU_BITABLE_TABLE_ID")

    missing = [name for name, val in [
        ("FEISHU_APP_ID", app_id),
        ("FEISHU_APP_SECRET", app_secret),
        ("FEISHU_BITABLE_APP_TOKEN", app_token),
        ("FEISHU_BITABLE_TABLE_ID", table_id),
    ] if not val]
    if missing:
        raise RuntimeError(f"缺少必需的环境变量: {', '.join(missing)}")

    print("→ 获取 tenant_access_token...")
    access_token = get_tenant_access_token(app_id, app_secret)
    print("→ 格式化字段...")
    fields = format_record_fields(script)
    print(f"→ 写入多维表格 (app_token={app_token[:10]}..., table={table_id[:10]}...)")
    record = write_record(app_token, table_id, fields, access_token)
    return record


def build_record_url(app_token: str, table_id: str, record_id: str) -> str:
    return f"https://feishu.cn/base/{app_token}?table={table_id}&record={record_id}"


def main():
    parser = argparse.ArgumentParser(description="把脚本写入飞书多维表格")
    parser.add_argument("--script", required=True, help="脚本 JSON 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只格式化不写入，用于调试")
    args = parser.parse_args()

    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    if args.dry_run:
        fields = format_record_fields(script)
        print("=== Dry Run: 格式化后的 fields ===")
        print(json.dumps(fields, ensure_ascii=False, indent=2))
        return 0
    try:
        record = write_script_to_bitable(script)
        print(f"\n✓ 写入成功")
        print(f"  record_id: {record.get('record_id')}")
        app_token = os.environ.get("FEISHU_BITABLE_APP_TOKEN")
        table_id = os.environ.get("FEISHU_BITABLE_TABLE_ID")
        if app_token and table_id and record.get("record_id"):
            url = build_record_url(app_token, table_id, record["record_id"])
            print(f"  链接: {url}")
        return 0
    except Exception as e:
        print(f"\n✗ 写入失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
