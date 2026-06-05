# 架构详解

## 数据流

```
                    ┌── GitHub Actions / 本地 ──┐
                    │                            │
DimbreathBot/       │  fetch_raw(game="genshin") │
AnimeGameData ──────→  (git sparse checkout)     │
(v6.6, 6.3 GB)     │  → ~740 MB 最小集           │
                    │                            │
                    │  extract_quests()           │
                    │  extract_talks()            │
                    │  extract_avatars()          │
                    │  extract_misc()             │
                    │     │                       │
                    │     ↓ JSONL (int → str)     │
                    │                            │
                    │  convert_*()                │
                    │     │                       │
                    │     ↓ .txt files            │
                    │                            │
                    └────────┬───────────────────┘
                             ↓
                    teyvat-story-archive
                    (纯 .txt, ~44 MB)
```

## 三层架构

### 1. Fetch 层 (`fetch.py`)

**职责**：获取 raw data 到本地磁盘

```python
fetch_raw("genshin", "/tmp/raw", proxy=...)
# → git clone --depth=1 --filter=blob:none --sparse
# → git sparse-checkout set --no-cone <paths>
```

- 通过环境变量读取仓库地址（不硬编码 URL）
- 使用 subprocess 调用 git（比 gitpython 更可靠地处理 sparse checkout）
- 默认路径集定义在 `GAME_PATHS` 字典中

### 2. Extract 层 (`extract/`)

**职责**：将 raw JSON 中的整数哈希替换为实际文本，输出 JSONL

**核心算法**：`replace_hashes(obj, text_map)`

```python
def replace_hashes(obj, text_map):
    if isinstance(obj, dict):
        return {k: replace_hashes(v, text_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_hashes(v, text_map) for v in obj]
    if isinstance(obj, int) and not isinstance(obj, bool):
        return text_map.get(str(obj), obj) or obj  # "" 时不替换
    return obj
```

**关键洞察**：原神 CodexQuest JSON 使用混淆 key 名（`OPKOJIEHJAE` 等），字段内容为整数哈希引用。通过**递归替换所有整数**而不是按字段名匹配，避免了 brittle 的 key 名解析。只有最终转换阶段需要知道 key 名。

**类继承**：

```
BaseExtractor (base.py)
    │
    ├── GenshinExtractor (genshin.py)
    │   - text_map_paths: TextMap + TextMap_Medium
    │   - quest_data_path: BinOutput/CodexQuest
    │   - extract_talks(), extract_avatars(), extract_misc()
    │
    ├── StarrailExtractor (starrail.py) — Phase 5 ✅
    │   - text_map_paths: TextMap + TextMapMain (single table, no Medium split)
    │   - stable hash: string → 32-bit hash for ExcelOutput field lookup
    │   - TalkSentenceConfig.json: TalkSentenceID → speaker/content hash mapping
    │   - quest_data: ExcelOutput/MainMission + SubMission + MissionChapterConfig
    │   - talk_data: Config/Level/{Mission,Story,TrainVisitor,Activity,Message}/
    │   - extract_quests(), extract_talks(), extract_avatars(), extract_misc()
    │
    └── ZZZExtractor (zzz.py) — Phase 6
```

### 3. Convert 层 (`convert.py`)

**职责**：将 JSONL 格式化为人类可读的 Markdown `.txt`

每种数据类型有独立的转换函数：
- `convert_quests()` / `convert_starrail_quests()` — 按 quest/mission 分文件
- `convert_talks()` / `convert_starrail_talks()` — 按 Talk 类型或来源类型分目录
- `convert_avatars()` / `convert_starrail_avatars()` — 按角色分文件
- `convert_misc()` / `convert_starrail_misc()` — 按条目分文件

## 星铁 TextMap 与哈希方案

星铁使用**单表 TextMap**（`TextMap{lang}.json` + `TextMapMain{lang}.json`），无 Medium 分拆。直接合并即可：

```python
text_map = merge_text_maps([
    "TextMap/TextMapCHS.json",       # 主文本 (~? entries)
    "TextMap/TextMapMainCHS.json",   # 补充文本
])
```

**stable hash**：部分 ExcelOutput 字段（如 `MissionChapterConfig` 中的章节名）的值是字符串，其 stable hash 作为 TextMap key。算法为社区参考实现（mrzjy/StarrailDialog）：

```python
def get_stable_hash(s: str) -> int:
    hash1 = hash2 = 5381
    i = 0
    while i < len(s) and s[i] != '\0':
        hash1 = ((hash1 << 5) + hash1) ^ ord(s[i])
        if i == len(s) - 1 or s[i + 1] == '\0':
            break
        hash2 = ((hash2 << 5) + hash2) ^ ord(s[i + 1])
        i += 2
    return (hash1 + (hash2 * 1566083941)) & 0xFFFFFFFF
```

**TalkSentenceConfig**：对话不直接嵌在剧情 JSON 中，而是通过 `TalkSentenceID` 间接引用：

```python
# TalkSentenceConfig.json
{
    "50001": {
        "TextmapTalkSentenceName": {"Hash": 100},
        "TalkSentenceText": {"Hash": 200}
    }
}
```

提取时先加载 `TalkSentenceConfig`，再通过 ID 查找说话人名称和内容哈希。

## 星铁对话序列结构

星铁剧情 JSON（`Config/Level/` 下的 `.json`）使用**序列化 TaskList**：

```json
{
    "OnStartSequece": [
        {
            "TaskList": [
                {"$type": "RPG.GameCore.PlayAndWaitSimpleTalk", "SimpleTalkList": [...]},
                {"$type": "RPG.GameCore.PlayOptionTalk", "OptionList": [...]},
                {"$type": "RPG.GameCore.WaitCustomString", "CustomString": {"Value": "TalkSentence_50003"}},
                {"$type": "RPG.GameCore.EndPerformance"}
            ]
        }
    ]
}
```

解析流程：
1. `_parse_on_sequence()` 遍历 `TaskList`，按 `$type` 分发处理
2. `_get_speaker_content()` 通过 `TalkSentenceID` 查 `TalkSentenceConfig` + TextMap
3. `_merge_sessions()` 去除 `WaitCustomString` 与 `PlayAndWaitSimpleTalk` 的重复

## TextMap 合并策略（原神）

原神需要合并两套 TextMap：

原神需要合并两套 TextMap：

```python
# 加载时
text_map = merge_text_maps([
    "TextMap/TextMapCHS.json",         # 对话内容 (~246K entries)
    "TextMap/TextMap_MediumCHS.json",  # Speaker 名称 (~547K entries)
])
# → 合并后 ~793K entries 的统一哈希表

# 一次 replace_hashes() 调用即可解析全部引用
quest = replace_hashes(quest, text_map)
```

## v6.6 Talk key 名适配

v6.6 的 Talk 数据有两套 key 结构：

**Type A**（Gadget/Npc/Quest/Activity/FreeGroup/NpcOther/NpcGroup）：
```
GALIDJOEHOC → dialog list
PIBKEGJOJHN → speaker role {_id, _type}
AIGJBMCHCJG → content hash
BMFGJJJPBBC → role name hash
```

**Type B**（Blossom/Coop/Cutscene/Storyboard）：
```
IOEDPLCPFFB → dialog list
DGGDDIMMIDO → speaker role
HJJLLECCCPI → content hash
```

提取阶段不关心 key 名（因为使用递归替换），只有转换阶段需要这些 key 名来定位说话人和对话内容字段。

## 添加新游戏的步骤

1. 调研该游戏的 raw data 结构（TextMap 格式、剧情数据路径）
2. 创建 `extract/yourgame.py` 继承 `BaseExtractor`
3. 设置 `game_name`、`text_map_paths`、`quest_data_path`
4. 如需非标准哈希方案，覆盖 `load_text_map()`
5. 如需非标准提取流程，覆盖 `extract_quests()`
6. 添加游戏特有的提取方法（如 `extract_talks()`）
7. 在 `convert.py` 添加对应的转换函数
8. 在 `cli.py` 注册游戏和命令
9. 在 `fetch.py` 添加默认 sparse checkout 路径
10. 编写测试
