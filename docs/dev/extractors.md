# 提取器开发指南

## 快速上手

添加一个新游戏的提取器，最少只需定义一个类：

```python
# extract/my_game.py
from hoyo_story.extract.base import BaseExtractor

class MyGameExtractor(BaseExtractor):
    game_name = "my-game"
    text_map_paths = ["TextMap/TextMap{lang}.json"]
    quest_data_path = "StoryData/Quests"
```

如果你游戏的 TextMap 使用简单整数哈希（类似原神），且剧情数据组织为 `StoryData/Quests/*.json` 的扁平结构，以上即全部代码。

## BaseExtractor 接口

```python
class BaseExtractor:
    # ── 子类必须覆盖 ──
    game_name: str = ""              # "genshin" / "starrail" / "zzz"
    text_map_paths: list[str] = []   # TextMap 文件相对路径（{lang} 占位符）
    quest_data_path: str = ""        # 剧情 JSON 目录相对路径

    # ── 可覆盖 ──
    def load_text_map(self) -> dict[str, str]: ...
    def extract_quests(self, output_path=None) -> str: ...

    # ── 已提供 ──
    raw_repo_path: str
    lang: str
```

## 自定义 TextMap 加载

如果你的游戏使用非标准哈希方案（如星铁的 xxhash），覆盖 `load_text_map()`：

```python
def load_text_map(self) -> dict[str, str]:
    path = os.path.join(
        self.raw_repo_path,
        f"TextMap/TextMap{self.lang}.json"
    )
    with open(path) as f:
        raw = json.load(f)
    # 自定义解析逻辑
    return {self._xxhash_to_int(k): v for k, v in raw.items()}
```

## 添加自定义提取方法

游戏特有文本类型（如原神的 NPC 对话、角色故事）通过额外方法提取：

```python
class MyGameExtractor(BaseExtractor):
    ...

    def extract_something(self, output_path=None) -> str:
        """提取某类特有文本为 JSONL。"""
        text_map = self.load_text_map()

        if output_path is None:
            output_path = f"something_{self.lang}.jsonl"

        with open(output_path, "w", encoding="utf-8") as out:
            for file in self._iter_data_files():
                with open(file) as f:
                    data = json.load(f)
                data = replace_hashes(data, text_map)
                if data:
                    out.write(json.dumps(data, ensure_ascii=False) + "\n")

        return output_path
```

## 辅助工具

### replace_hashes(obj, text_map)

递归替换所有整数为 TextMap 文本。适用于任何 JSON 结构。

### merge_text_maps(paths)

加载并合并多个 TextMap JSON 文件。

### 如何使用

```python
from hoyo_story.extract.base import replace_hashes, merge_text_maps

# 加载 TextMap
text_map = merge_text_maps([
    "TextMap/TextMapCHS.json",
    "TextMap/TextMap_MediumCHS.json",
])

# 递归替换哈希
quest = json.load(open("quest_1000.json"))
quest = replace_hashes(quest, text_map)
# 所有整数哈希已被替换为实际文本
```

## 注意事项

### 仅加载游戏特有的 TextMap

不要为了"方便"而把其他游戏的 TextMap 路径加到 `text_map_paths`。每个游戏的哈希空间可能冲突。

### 保持 JSONL 格式一致

提取阶段的 JSONL 是"已替换哈希的原始 JSON 树"。不要在此阶段做格式转换——那是 convert 层的职责。

### 处理 JSON 解码错误

raw data 中可能存在格式异常的 JSON 文件。使用 try/except 跳过：

```python
try:
    data = json.load(f)
except json.JSONDecodeError:
    continue
```

### 给每行数据加元数据标签

在 JSONL 中加 `_type`、`_file` 等前缀下划线字段，方便 convert 层分组和命名：

```python
data["_talk_type"] = "Npc"       # 供 convert 阶段分组
data["_talk_file"] = file_name   # 供 convert 阶段命名
```

这些字段以 `_` 开头，不会与游戏数据字段冲突。
