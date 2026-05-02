# risk_check.py 跑通后的发现

> 用 `output/sample_script_catherine.json`（手写 demo 脚本，模拟 Step 3 LLM 输出）跑了端到端 Step 4–6，发现两个 risk_check.py 误报问题。记下来等下版本修。

## 跑通的环节

```
sample_script_catherine.json (手写)
  → Step 4 derive_storyboard()        ✓ 8 镜分镜表
  → Step 5 risk_check.check_script()  ⚠ 见下
  → Step 6 write_to_feishu --dry-run   ✓ fields 格式正确
```

## 发现的两个误报

### 1. 复合词误报：「第一」命中「第一视角」

```
field: product_insertion.action_shots[0]
matched: "第一" (extreme_words 类)
context: "第一视角拿起希腊酸奶"
```

「第一视角」是镜头语言术语，不是广告法极限词。risk_check 的关键词扫描没做词边界判断，凡是包含「第一」二字就报。

**修复方向**：

- 短期：在 forbidden_words.md 的极限词条目里给「第一」加排除前缀清单（`第一视角`、`第一次`、`第一人称`）
- 长期：scan_extreme_words 引入分词器（如 jieba）按词扫描，而不是子串匹配
- 也可以：把「第一」改为正则 `(?<![一-龥])第一(?![视人感])`，但脆弱

### 2. 否定上下文误报：compliance_notes 反而被扫成命中

```
field: compliance_notes[2]
matched: "减肥" + "降糖"
context: "全程不出现「减肥」「瘦」「降糖」等词，不与身材话题挂钩"
```

`compliance_notes` 字段写的是「博主拍摄时**注意不要用**这些词」的提醒，本身是合规元数据，不是脚本可见文案。risk_check 对所有字符串字段一视同仁地扫，把元数据也扫了。

**修复方向**：

- 在 `collect_text_fields` 里增加 `EXCLUDE_PATHS = {"compliance_notes", "compliance_report", "meta", "script_id", "creator.id"}` 之类的字段白名单
- 或者：扫描时对每个文本字段先用 LLM/正则判断「这是产品文案」还是「合规提示」。前者更便宜。

## 验证用例补充建议

把这两个误报样本写进 `tests/test_risk_check.py`，作为 regression：

```python
def test_extreme_words_no_false_positive_on_compound(forbidden):
    s = clean_script_with_field("第一视角拿起希腊酸奶")
    hits = scan_extreme_words(s, forbidden)
    assert not any(h["word"] == "第一" for h in hits)

def test_compliance_notes_excluded_from_scan(forbidden):
    s = clean_script_with_compliance_note("不要用减肥、降糖等词")
    report = check_script(s, ...)
    assert report["compliance_status"] != "拦截"
```

但现在这两条还没修，本仓库的 pytest 套件应该不加上去（会失败）。先等修完一起加。

## 飞书 fields 验证

write_to_feishu 的 `format_record_fields` 输出经检视格式正确，能对接飞书 bitable。注意几点：

- `生成时间` 是毫秒 epoch（1777620945804）。在飞书后台需要把对应字段类型设为「日期」并选「时间戳」格式。
- `分镜表` 是 JSON 字符串，飞书 bitable 的「多行文本」字段容量上限 50000 字符，本 demo 只用了 ~3000 字，安全。
- `质检详情` 同上，本 demo 输出 `"{}"` 因为 demo 脚本没填 compliance_report 字段；真实 pipeline 中 risk_check.check_script 会填好。

## 结论

集成链路（Step 4–6）跑通无障碍。risk_check 关键词扫描层有上面两个误报需要修。等 LLM call（Step 3）有可用 API key 后跑真生成脚本，能验证 prompt 质量和博主调性还原度。
