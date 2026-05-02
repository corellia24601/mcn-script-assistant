"""脚本生成与质检共用的 Pydantic Schema。

字段定义对应 references/output_schema.md。改字段时两边一起改。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RiskLevel = Literal["H", "M", "L"]
HookType = Literal["pain_point", "scene", "question", "counterintuitive"]


class Hook(BaseModel):
    text: str = Field(..., max_length=30)
    visual: str = Field(..., max_length=80)
    type: HookType


class Scene(BaseModel):
    order: int = Field(..., ge=1, le=20)
    duration_sec: int = Field(..., ge=2, le=30)
    scene: str = Field(..., max_length=80)
    voiceover: str = Field(..., max_length=100)
    on_screen_text: str = Field(default="", max_length=30)


class RiskFlag(BaseModel):
    level: RiskLevel
    matched: str
    location: str
    rule: str
    suggestion: str = ""


class ScriptMeta(BaseModel):
    model: str
    skill_version: str
    generated_at: datetime
    brief_version: str


class Script(BaseModel):
    """单条小红书短视频脚本的完整结构。"""

    blogger_id: str
    script_id: str
    platform: Literal["xiaohongshu"] = "xiaohongshu"
    video_length_sec: int = Field(..., ge=30, le=90)
    hook: Hook
    scenes: list[Scene] = Field(..., min_length=3, max_length=6)
    cta: str = Field(..., max_length=60)
    tags: list[str] = Field(..., min_length=5, max_length=10)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    meta: ScriptMeta

    @field_validator("tags")
    @classmethod
    def _no_hash_in_tags(cls, v: list[str]) -> list[str]:
        # 小红书 tag 写入时不带 # 号，由前端拼接
        for tag in v:
            if "#" in tag:
                raise ValueError(f"tag 不应包含 #：{tag!r}")
            if not tag.strip():
                raise ValueError("tag 不能为空")
        return v

    @model_validator(mode="after")
    def _scene_duration_sum(self) -> "Script":
        total = sum(s.duration_sec for s in self.scenes)
        # 允许 ±5 秒误差
        if abs(total - self.video_length_sec) > 5:
            raise ValueError(
                f"scenes 总时长 {total}s 与 video_length_sec {self.video_length_sec}s 偏差超过 5s"
            )
        return self

    @model_validator(mode="after")
    def _scene_order_unique(self) -> "Script":
        orders = [s.order for s in self.scenes]
        if len(orders) != len(set(orders)):
            raise ValueError("scenes 的 order 字段必须唯一")
        return self


__all__ = [
    "Hook",
    "Scene",
    "RiskFlag",
    "RiskLevel",
    "Script",
    "ScriptMeta",
]
