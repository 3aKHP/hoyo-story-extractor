# 测试指南

## 运行测试

```bash
uv run pytest                    # 全部测试
uv run pytest -v                 # 详细输出
uv run pytest tests/test_extract_base.py  # 单个模块
uv run pytest -k "test_replace"  # 按名称筛选
```

## 测试结构

```
tests/
├── test_extract_base.py    ← replace_hashes, merge_text_maps, BaseExtractor
├── test_extract_genshin.py ← GenshinExtractor
├── test_convert.py         ← 所有转换器
├── test_fetch.py           ← get_repo_url, fetch_raw
└── test_cli.py             ← CLI happy path and user-friendly failures
```

## 当前覆盖

45 个测试：

| 模块 | 测试数 | 覆盖内容 |
|------|:---:|------|
| `test_extract_base.py` | 20 | `replace_hashes` (11 边界情况), `merge_text_maps` (5), `BaseExtractor` (4) |
| `test_extract_genshin.py` | 7 | `GenshinExtractor` 属性、TextMap 合并、端到端提取 |
| `test_convert.py` | 6 | quest 转换、空 quest、多子任务、旁白、`clean_variables` |
| `test_fetch.py` | 8 | `get_repo_url` 环境变量、无效游戏、`fetch_raw`、路径配置 |
| `test_cli.py` | 4 | CLI 缺环境变量、缺 raw 数据、未实现游戏、最小 pipeline 烟测 |

## 编写测试

### 模式：使用 tmp_path fixture

```python
def test_something(self, tmp_path: Path) -> None:
    # 创建临时文件
    f = tmp_path / "test.json"
    f.write_text('{"key": "value"}', encoding="utf-8")

    # 运行被测代码
    result = my_function(str(f))

    # 断言
    assert result == expected
```

### 模式：使用 monkeypatch 设置环境变量

```python
def test_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENSHIN_RAW_REPO", "https://example.com/repo.git")
    assert get_repo_url("genshin") == "https://example.com/repo.git"
```

### 模式：参数化测试

```python
@pytest.mark.parametrize(
    ("obj", "text_map", "expected"),
    [
        (42, {"42": "life"}, "life"),
        (42, {}, 42),
        (None, {}, None),
    ],
)
def test_scalar_values(self, obj, text_map, expected) -> None:
    assert replace_hashes(obj, text_map) == expected
```

## 集成测试

真实数据测试使用 `local_prod/` 中的 v6.6 数据：

```python
RAW = "local_prod/genshin_raw"  # 或通过环境变量指定

def test_full_pipeline():
    ext = GenshinExtractor(RAW, lang="CHS")
    jsonl = ext.extract_quests()
    files = convert_quests(jsonl, "/tmp/output")
    assert len(files) == 483
```

> ⚠️ 集成测试需要 raw data，不应在 CI 中运行。在 CI 中只跑单元测试。

## CI 配置

```yaml
# .github/workflows/ci.yml
- name: Test with pytest
  run: uv run pytest --cov=src/hoyo_story --cov-report=term-missing
- name: Build package
  run: uv build
```

CI 矩阵：Python 3.11 / 3.12 / 3.13。
