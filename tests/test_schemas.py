"""Pydantic schema 校验测试。"""
from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from schemas import Script


def test_clean_script_validates(sample_script_dict):
    s = Script.model_validate(sample_script_dict)
    assert s.video_length_sec == 60
    assert len(s.scenes) == 3


def test_video_length_out_of_range(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["video_length_sec"] = 120  # > 90
    with pytest.raises(ValidationError):
        Script.model_validate(d)


def test_scenes_too_few(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["scenes"] = d["scenes"][:2]
    d["video_length_sec"] = 40
    d["scenes"][0]["duration_sec"] = 20
    d["scenes"][1]["duration_sec"] = 20
    with pytest.raises(ValidationError):
        Script.model_validate(d)


def test_duration_sum_mismatch(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    # 总和与 video_length_sec 偏差 > 5
    d["scenes"][0]["duration_sec"] = 5
    d["scenes"][1]["duration_sec"] = 5
    d["scenes"][2]["duration_sec"] = 5  # 总 15s vs 60s
    with pytest.raises(ValidationError, match="偏差"):
        Script.model_validate(d)


def test_duplicate_scene_order(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["scenes"][1]["order"] = 1  # 与第一条重复
    with pytest.raises(ValidationError, match="order"):
        Script.model_validate(d)


def test_tags_no_hash(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["tags"] = ["#希腊酸奶"] + d["tags"][1:]
    with pytest.raises(ValidationError, match="#"):
        Script.model_validate(d)


def test_tags_min_length(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["tags"] = ["a", "b"]
    with pytest.raises(ValidationError):
        Script.model_validate(d)


def test_hook_text_max_length(sample_script_dict):
    d = copy.deepcopy(sample_script_dict)
    d["hook"]["text"] = "钩" * 31
    with pytest.raises(ValidationError):
        Script.model_validate(d)
