# 转换器开发指南

## 架构

转换器将提取阶段产出的 JSONL（已替换哈希的原始 JSON 树）格式化为人类可读的 `.txt`。

转换器函数签名统一为：

```python
def convert_xxx(jsonl_path: str, output_dir: str) -> list[str]:
    """返回生成的文件路径列表"""
```

唯一例外是 `convert_quests()`，它额外接受一个版本参数（见下文
「版本感知的 quest 转换」）。

## 现有转换器

| 函数 | 输入 | 输出 |
|------|------|------|
| `convert_quests()` | quest JSONL | 按 quest 分文件 `.txt` |
| `convert_talks()` | talk JSONL | 按 Talk 类型分目录 `.txt` |
| `convert_avatars()` | avatar JSONL | 按角色分文件 `.txt` |
| `convert_misc()` | misc JSONL | 按条目分文件 `.txt` |

## 版本感知的 quest 转换

原神 CodexQuest 在 6.6、6.7、7.0 分别使用一组混淆字段，7.2 使用明文字段。
`convert_quests()` 通过版本映射读取这些结构：

```python
def convert_quests(jsonl_path: str, output_dir: str, data_version: str | None = None) -> list[str]
```

- `data_version=None`：从首个 quest 的顶层 key 自动探测版本
  （`detect_quest_version()`，定义在 `extract/base.py`）
- `data_version="7.0"` 等：跳过探测，直接使用对应版本的表

key 映射表定义在 `extract/base.py` 的 `QUEST_KEY_MAPS`，每个版本登记
7 个语义角色 → 混淆 key 的映射：

| 语义角色 | 6.6 | 7.0 |
|------|------|------|
| `text`（文本对象内 hash 字段） | `OPKOJIEHJAE` | `BNJEGIAOKGM` |
| `speaker`（item 上说话人） | `KDDMHACHOGH` | `IILBCFJNPGA` |
| `dialogs`（item 内对话列表） | `JOIPGFEDKFO` | `OFKGPGLHIDJ` |
| `text_obj`（对话条目内文本对象） | `LEMPMANEBOB` | `JGPDCLOJKLC` |
| `subquests`（顶层子任务列表） | `IKECHKLEFFK` | `EBNBLBEIFFJ` |
| `items`（子任务内条目） | `DLLOBLBEBPM` | `PEAKPGNONFA` |
| `subq_title`（子任务标题对象） | `CGJPNLJCKKB` | `OGEGCCLHIHP` |

**接入新版本（如 7.1）的步骤**：

1. 抓取一份该版本的 `BinOutput/CodexQuest/*.json`,对照语义找到 7 个角色对应的混淆 key
2. 在 `QUEST_KEY_MAPS` 增加一个版本条目
3. 在 `tests/test_extract_base.py` 的 `TestQuestKeyMaps` 加断言(可选)
4. 本地用真实数据验证 `convert_quests(..., data_version="7.1")` 产出正确

## Talk 的版本兼容(6.6 / 7.0)

Talk 转换器在 7.0 发生了两处变化,均已适配:

1. **TextMap 偏移(v6.7+)**：上游把 Talk 对话内容从 `TextMap_Medium{lang}.json`
   移入 `TextMap{lang}.json`,且所有 key 偏移 **+512**。因此 Talk 文件里存的
   内容 hash `H` 需要查询 `TextMap[H + 512]`。`GenshinExtractor.load_text_map()`
   为 CHS 每个 key `K` 额外注册 `K - 512` 别名(`setdefault`,直接命中优先),
   对 quest / avatar 的既有直接命中无影响。6.6 数据不需要偏移,但该别名
   逻辑在 6.6 上也安全(不会覆盖已有映射)。

2. **Type B key 重混淆**：7.0 将 6.6 的 Type B 字段全部重命名
   (`IOEDPLCPFFB` → `PFALHAKIILD`, `DGGDDIMMIDO` → `LFGCLNLPAPB`,
   `HJJLLECCCPI` → `OACNIBLFFDI`),Type A 字段不变。`convert_talks()` 通过
   `_TALK_FORMATS` 表按顶层 list key 自动识别格式,同时兼容:
   - 6.6 Type A / Type B 旧 key
   - 7.0 新混淆 key
   - 少量明文 key 文件(`dialogList` / `talkRole` / `talkContentTextMapHash`)
   - Group 类文件(仅条件无对话,自动跳过)

**Excel 转换不受影响**：Excel 使用语义 key（`nameTextMapHash` 等），
6.6–7.0 未变。

## Genshin 7.2

7.2 的 CodexQuest 使用明文字段。`QUEST_KEY_MAPS["7.2"]` 依次登记
`textId`、`speakerText`、`dialogs`、`text`、`subQuests`、`items` 与
`subQuestTitle`。转换器通过 `mainQuestTitle`、`mainQuestDesp`、`chapterNum`
和 `chapterTitle` 读取任务头部，输出不依赖 JSON 字段顺序。

Talk 同时包含明文 `dialogList` 及保留的混淆格式；`_TALK_FORMATS` 登记这几种
已核验的布局。提取层将缺省的 NPC 名称写入派生字段 `_speaker_name`，名称来自
同一快照的 NPC 表；转换层优先读取显式名称，再读取该派生字段。

`convert_avatars()` 使用 `{序号:04d}_{名称}.txt`，同名角色记录保持独立。
真实数据验证应同时比较返回条目数、实际文件数及各原始文本字段在输出中的覆盖，
并单列 TextMap 未收录的哈希。合成测试位于 `tests/test_genshin_v72.py`。

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
