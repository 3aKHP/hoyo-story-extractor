# 转换器开发指南

## 架构

转换器将提取阶段产出的 JSONL（已替换哈希的原始 JSON 树）格式化为人类可读的 `.txt`。

转换器函数签名统一为：

```python
def convert_xxx(jsonl_path: str, output_dir: str) -> list[str]:
    """返回生成的文件路径列表"""
```

## 现有转换器

| 函数 | 输入 | 输出 |
|------|------|------|
| `convert_quests()` | quest JSONL | 按 quest 分文件 `.txt` |
| `convert_talks()` | talk JSONL | 按 Talk 类型分目录 `.txt` |
| `convert_avatars()` | avatar JSONL | 按角色分文件 `.txt` |
| `convert_misc()` | misc JSONL | 按条目分文件 `.txt` |

## 添加新转换器

### 1. 确定输入格式

提取阶段产出的 JSONL 每行是一个已替换哈希的 dict。例如 Talk：

```json
{
  "GALIDJOEHOC": [
    {
      "PIBKEGJOJHN": {"_id": "1780", "_type": "TALK_ROLE_NPC"},
      "AIGJBMCHCJG": "你好，旅行者！",
      ...
    }
  ],
  "AADKDKPMGNO": 6865006,
  "HAHEIAHBPEJ": "NPC",
  "_talk_type": "Npc",
  "_talk_file": "01213b14.json"
}
```

### 2. 理解 post-replace_hashes 的数据结构

关键区别：提取阶段后，**原本是整数哈希的字段现在变成了字符串文本**。

```python
# 提取前
{"AIGJBMCHCJG": 1084138786}

# 提取后 (replace_hashes 已完成)
{"AIGJBMCHCJG": "你好，旅行者！"}
```

因此转换器的策略是：
1. 从已知 key 名中读取字段（key 名不变，但 value 从 int 变成了 str）
2. 检查 value 类型：`str` = 已替换的文本，`int` = 未被替换（不在 TextMap 中）
3. 格式化输出

### 3. 编写转换函数

```python
def convert_my_type(jsonl_path: str, output_dir: str) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            # ... 格式化 ...
            fpath = out / f"{name}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written
```

### 4. 在 CLI 中注册

```python
# cli.py
from hoyo_story.convert import convert_my_type

# 在 converters dict 中添加
converters = {
    ...
    "my-type": convert_my_type,
}
```

## 命名规范

- 函数名：`convert_<复数类型>`（`convert_quests`、`convert_talks`）
- 文件名：`{序号}_{名称}.txt`（`0001_浮世浮生千岩间.txt`）
- 文件名清理：移除 `\/:*?"<>|` 字符，限制 100 字符

## 导出策略

| 策略 | 适用场景 | 示例 |
|------|------|------|
| 按 title 分文件 | 每行有唯一标题 | quests, avatars |
| 按类型分目录 + 按 ID 分文件 | 数据量大，需分组 | talks |
| 按条目分文件 | 每行是独立实体 | misc |

## 文本格式约定

```markdown
# 标题           ← 一级标题

*描述文本*       ← 斜体描述

> 元信息         ← 引用块（章节号等）

### 子章节        ← 三级标题

**说话人**：台词  ← 对话（粗体说话人 + 全角冒号）

普通文本         ← 舞台指示 / 旁白
```

全角冒号 `：`（U+FF1A）用于中文文本，保持与原神游戏内显示一致。
