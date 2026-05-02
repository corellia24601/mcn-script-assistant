"""批量写入飞书多维表格。

CLI:
    python -m feishu.write_to_feishu records.json            # dry-run，只打印
    python -m feishu.write_to_feishu records.json --commit   # 真写入

约束（CLAUDE.md）：
- 默认 dry-run，--commit 才真写
- tenant_access_token 缓存到内存，2 小时内复用
- 写入走 bitable v1 batch_create，每批最多 500 条
- 所有外部失败抛 FeishuError，结构化错误信息
- 没有 hardcode 任何凭证；从 .env 读
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

LARK_BASE = "https://open.feishu.cn/open-apis"
DEFAULT_TIMEOUT_SEC = 15
TOKEN_REFRESH_BUFFER_SEC = 300  # 提前 5 分钟换 token，避免边界过期
BATCH_SIZE = 500  # bitable v1 单次上限

logger = logging.getLogger("feishu.write")


class FeishuError(Exception):
    """飞书 API 调用失败时抛出，承载结构化错误。"""

    def __init__(self, code: int, msg: str, *, raw: dict[str, Any] | None = None):
        super().__init__(f"[{code}] {msg}")
        self.code = code
        self.msg = msg
        self.raw = raw or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "msg": self.msg, "raw": self.raw}


class FeishuConfig(BaseModel):
    app_id: str = Field(..., min_length=1)
    app_secret: str = Field(..., min_length=1)
    app_token: str = Field(..., min_length=1, description="bitable app token")
    table_id: str = Field(..., min_length=1)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "FeishuConfig":
        src = env if env is not None else os.environ
        missing = [
            k
            for k in (
                "FEISHU_APP_ID",
                "FEISHU_APP_SECRET",
                "FEISHU_BITABLE_APP_TOKEN",
                "FEISHU_BITABLE_TABLE_ID",
            )
            if not src.get(k)
        ]
        if missing:
            raise FeishuError(
                -1,
                f"missing env vars: {', '.join(missing)}",
            )
        return cls(
            app_id=src["FEISHU_APP_ID"],
            app_secret=src["FEISHU_APP_SECRET"],
            app_token=src["FEISHU_BITABLE_APP_TOKEN"],
            table_id=src["FEISHU_BITABLE_TABLE_ID"],
        )


class _TokenCache:
    """内存版 tenant_access_token 缓存。"""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get(self) -> str | None:
        if self._token and self._expires_at - time.time() > 0:
            return self._token
        return None

    def set(self, token: str, expires_in_sec: int) -> None:
        # 飞书最长返回 7200，留 buffer 提前刷新
        ttl = max(60, min(expires_in_sec, 7200) - TOKEN_REFRESH_BUFFER_SEC)
        self._token = token
        self._expires_at = time.time() + ttl

    def clear(self) -> None:
        self._token = None
        self._expires_at = 0.0


class FeishuClient:
    """轻量飞书多维表格客户端，只暴露本项目用得到的接口。"""

    def __init__(
        self,
        config: FeishuConfig,
        *,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout = timeout
        self._cache = _TokenCache()

    def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise FeishuError(-1, f"http error: {e}") from e
        try:
            data = resp.json()
        except ValueError as e:
            raise FeishuError(
                resp.status_code,
                f"non-json response (status={resp.status_code}): {resp.text[:200]}",
            ) from e
        if data.get("code") != 0:
            raise FeishuError(int(data.get("code", -1)), str(data.get("msg", "unknown")), raw=data)
        return data

    def get_tenant_access_token(self, *, force_refresh: bool = False) -> str:
        if not force_refresh:
            cached = self._cache.get()
            if cached:
                return cached
        url = f"{LARK_BASE}/auth/v3/tenant_access_token/internal"
        data = self._request_json(
            "POST",
            url,
            json={
                "app_id": self.config.app_id,
                "app_secret": self.config.app_secret,
            },
        )
        token = data.get("tenant_access_token")
        if not token:
            raise FeishuError(-1, "tenant_access_token missing in response", raw=data)
        self._cache.set(token, int(data.get("expire", 7200)))
        return token

    def add_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """批量写入，自动分片到 BATCH_SIZE。

        records 元素接受两种形态：
        - {"字段名": value, ...}（自动包一层 fields）
        - {"fields": {"字段名": value, ...}}
        """
        if not records:
            return {"code": 0, "msg": "no records", "inserted": 0, "results": []}

        normalized = [_ensure_fields_envelope(r) for r in records]
        token = self.get_tenant_access_token()
        url = (
            f"{LARK_BASE}/bitable/v1/apps/{self.config.app_token}"
            f"/tables/{self.config.table_id}/records/batch_create"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        inserted = 0
        results: list[dict[str, Any]] = []
        for batch in _chunks(normalized, BATCH_SIZE):
            data = self._request_json(
                "POST", url, headers=headers, json={"records": batch}
            )
            results.append(data.get("data", {}))
            inserted += len(batch)
            logger.info("batch_create ok: %d rows", len(batch))
        return {"code": 0, "msg": "ok", "inserted": inserted, "results": results}


def _ensure_fields_envelope(record: dict[str, Any]) -> dict[str, Any]:
    if "fields" in record and isinstance(record["fields"], dict):
        return {"fields": record["fields"]}
    return {"fields": record}


def _chunks(seq: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _load_records(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"{path} 必须是 JSON 数组，实际为 {type(raw).__name__}")
    return raw


def _summarize_dry_run(records: Iterable[dict[str, Any]], limit: int = 2) -> None:
    records = list(records)
    logger.info("DRY-RUN: 待写入 %d 条记录，预览前 %d 条", len(records), limit)
    for r in records[:limit]:
        logger.info(json.dumps(_ensure_fields_envelope(r), ensure_ascii=False))
    logger.info("加 --commit 才会真正写入飞书")


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="批量写入飞书多维表格（默认 dry-run）"
    )
    parser.add_argument("input", type=Path, help="JSON 数组文件路径")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="显式开启写入；不传则 dry-run（与 .env 中 FEISHU_COMMIT 任一为真即写入）",
    )
    parser.add_argument("--env", type=Path, default=None, help=".env 文件路径，默认按 dotenv 标准查找")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="打印 DEBUG 级日志",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.env:
        load_dotenv(args.env, override=False)
    else:
        load_dotenv(override=False)

    records = _load_records(args.input)

    commit_env = os.environ.get("FEISHU_COMMIT", "").strip().lower() in {"1", "true", "yes"}
    commit = args.commit or commit_env

    if not commit:
        _summarize_dry_run(records)
        return 0

    try:
        cfg = FeishuConfig.from_env()
        client = FeishuClient(cfg)
        result = client.add_records(records)
    except FeishuError as e:
        logger.error("飞书写入失败: %s", e.to_dict())
        return 2

    logger.info("写入完成：%s 条", result.get("inserted"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_cli())
