\# output 目录说明



本目录是 `run\_pipeline.py` 端到端跑完后的产物存放处，评审可直接打开查看。



\## 文件清单



| 文件 | 来源 | 用途 |

|---|---|---|

| `final\_script\_catherine\_xiaoxiong.{json,md}` | run\_pipeline.py 真生成 | Catherine 的 78s 短视频脚本（含分镜表 7 镜） |

| `final\_script\_couhuohuo.{json,md}` | run\_pipeline.py 真生成 | 凑活活的 78s 短视频脚本（含分镜表 8 镜） |

| `recheck\_\*.json` | risk\_check.py 后置质检报告 | 4 层质检全部通过的留痕证据 |



\## 质检状态



两条 final\_script 在最新 risk\_check 下都标 \*\*status=通过\*\*：

\- 极限词扫描：0 命中

\- 隐性违规：0 命中

\- 结构约束：0 命中

\- LLM-as-Judge：可选，未启用时不影响



详见各文件头部的 `compliance\_report` 字段，或 `recheck\_\*.json`。



\## 怎么从这些产物追溯生成过程



\- prompt 见 `prompts/main\_generation\_v4\_final.md`

\- 生成 pipeline 见 `skills/mcn-script-assistant/scripts/run\_pipeline.py`

\- 质检规则见 `skills/mcn-script-assistant/scripts/risk\_check.py` + `references/forbidden\_words.md`

\- 飞书写入证据见 `feishu/screenshots/`

