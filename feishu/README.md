# feishu/

> 本目录的 `write_to_feishu.py` 是 `skills/mcn-script-assistant/scripts/write_to_feishu.py`
> 的同步副本，与 SKILL.md Step 6 调用的是同一份代码。两份保持完全一致以方便评审从
> 任意一处入口阅读。

## 两份 write_to_feishu.py 的关系

| | `feishu/write_to_feishu.py` | `skills/.../scripts/write_to_feishu.py` |
|---|---|---|
| 定位 | 可独立使用的批量写入模块 | Skill Step 6 调用的单条写入模块 |
| 写入方式 | `batch_create`（最多 500 条/次） | 单条 `add_record` |
| Token 缓存 | 内存缓存，2h 自动刷新 | 每次调用重新获取 |
| CLI 入口 | `python -m feishu.write_to_feishu records.json --commit` | `python write_to_feishu.py --script out.json` |
| 测试覆盖 | `tests/test_feishu.py` | `tests/test_write_to_feishu.py` |

两份实现共享相同的环境变量和业务逻辑，但接口不同——本目录版本适合批量归档场景，Skill 内版本适合单次生成后立即写入。

## 使用

```bash
# Dry-run，只打印预览
uv run python -m feishu.write_to_feishu records.json

# 实际写入（需 FEISHU_* 凭证 + 显式 --commit）
uv run python -m feishu.write_to_feishu records.json --commit
```

## 环境变量

```
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_BITABLE_APP_TOKEN
FEISHU_BITABLE_TABLE_ID
```

详见仓库根 `.env.example`。

## 截图

`screenshots/` 目录存放飞书开放平台配置截图（应用凭证、权限、发布版本、多维表格字段），用于评审追溯。
