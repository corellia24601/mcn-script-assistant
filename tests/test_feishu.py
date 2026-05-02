"""飞书写入脚本测试。所有外部 HTTP 全部 mock，不发真请求。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from feishu.write_to_feishu import (
    BATCH_SIZE,
    FeishuClient,
    FeishuConfig,
    FeishuError,
    _chunks,
    _ensure_fields_envelope,
    _TokenCache,
    run_cli,
)


# ---- 单元 ----


def test_chunks_basic():
    assert list(_chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_chunks_empty():
    assert list(_chunks([], 10)) == []


def test_envelope_unwrapped():
    assert _ensure_fields_envelope({"a": 1}) == {"fields": {"a": 1}}


def test_envelope_already_wrapped():
    assert _ensure_fields_envelope({"fields": {"a": 1}}) == {"fields": {"a": 1}}


def test_token_cache_returns_none_when_empty():
    c = _TokenCache()
    assert c.get() is None


def test_token_cache_returns_value_until_expiry():
    c = _TokenCache()
    c.set("tok", 7200)
    assert c.get() == "tok"
    c.clear()
    assert c.get() is None


def test_config_from_env_missing_raises():
    with pytest.raises(FeishuError) as exc:
        FeishuConfig.from_env(env={})
    assert "missing env vars" in exc.value.msg


def test_config_from_env_ok():
    cfg = FeishuConfig.from_env(
        env={
            "FEISHU_APP_ID": "a",
            "FEISHU_APP_SECRET": "b",
            "FEISHU_BITABLE_APP_TOKEN": "c",
            "FEISHU_BITABLE_TABLE_ID": "d",
        }
    )
    assert cfg.app_id == "a" and cfg.table_id == "d"


# ---- 客户端 ----


def _mk_resp(json_payload: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_payload
    r.text = json.dumps(json_payload)
    return r


@pytest.fixture
def cfg() -> FeishuConfig:
    return FeishuConfig(
        app_id="cli_x",
        app_secret="sec_x",
        app_token="bascn_x",
        table_id="tbl_x",
    )


def test_get_token_caches(cfg):
    sess = MagicMock()
    sess.request.return_value = _mk_resp(
        {"code": 0, "msg": "ok", "tenant_access_token": "T1", "expire": 7200}
    )
    client = FeishuClient(cfg, session=sess)
    t1 = client.get_tenant_access_token()
    t2 = client.get_tenant_access_token()
    assert t1 == "T1" == t2
    # 第二次不应再发请求
    assert sess.request.call_count == 1


def test_get_token_propagates_api_error(cfg):
    sess = MagicMock()
    sess.request.return_value = _mk_resp({"code": 99991663, "msg": "app_secret error"})
    client = FeishuClient(cfg, session=sess)
    with pytest.raises(FeishuError) as e:
        client.get_tenant_access_token()
    assert e.value.code == 99991663


def test_add_records_batches(cfg):
    sess = MagicMock()

    def _request(method, url, **kw):
        if "tenant_access_token" in url:
            return _mk_resp(
                {"code": 0, "msg": "ok", "tenant_access_token": "T", "expire": 7200}
            )
        # batch_create
        return _mk_resp({"code": 0, "msg": "ok", "data": {"records": []}})

    sess.request.side_effect = _request

    client = FeishuClient(cfg, session=sess)
    n = BATCH_SIZE + 3  # 强制分两批
    result = client.add_records([{"f": i} for i in range(n)])
    assert result["inserted"] == n
    # 1 次拿 token + 2 次 batch_create = 3
    assert sess.request.call_count == 3


def test_add_records_empty_short_circuits(cfg):
    sess = MagicMock()
    client = FeishuClient(cfg, session=sess)
    out = client.add_records([])
    assert out["inserted"] == 0
    sess.request.assert_not_called()


def test_add_records_propagates_http_error(cfg):
    sess = MagicMock()
    sess.request.side_effect = requests.ConnectionError("boom")
    client = FeishuClient(cfg, session=sess)
    with pytest.raises(FeishuError, match="http error"):
        client.add_records([{"f": 1}])


# ---- CLI ----


def test_cli_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    p = tmp_path / "rec.json"
    p.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    # 即使 env 缺失也不能爆，因为是 dry-run
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_COMMIT", raising=False)
    code = run_cli([str(p)])
    assert code == 0


def test_cli_commit_requires_env(tmp_path, monkeypatch):
    p = tmp_path / "rec.json"
    p.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    for k in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BITABLE_APP_TOKEN", "FEISHU_BITABLE_TABLE_ID"):
        monkeypatch.delenv(k, raising=False)
    code = run_cli([str(p), "--commit"])
    assert code == 2  # FeishuError
