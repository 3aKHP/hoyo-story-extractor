# 常见问题

## 数据相关

### 为什么提取出来的台词里还有 `{NICKNAME}`？

游戏文本中有大量根据玩家选择动态替换的变量。目前这些变量**保留原样**未做替换。计划在 `clean_variables()` 中提供可选的替换策略（如 `{NICKNAME}` → `旅行者`）。

### 任务数量为什么和 wiki 对不上？

CodexQuest 中的每个 JSON 文件是任务的一个**子段**（sub-act），不是完整的任务。例如「浮世浮生千岩间」在数据中是 6 个子段文件，每个文件对应一段连续的剧情。一个命名任务可能对应 1-10 个文件。

### 空月之歌有第十幕但 wiki 只有九幕？

v6.6 数据中空月之歌有 11 个 act（序奏 + 第一~第十幕）。第十幕「道成千壑，因果异灭」是 v6.6 新增内容，wiki 可能尚未更新。

### TextMap 的中哈希（Medium）有什么用？

原神使用两套独立的 TextMap：
- `TextMap{lang}.json`（~246K entries）：对话内容、任务标题、描述
- `TextMap_Medium{lang}.json`（~547K entries）：说话人名称、NPC 名字

提取时会自动合并两套表，在一个 `replace_hashes()` 调用中递归替换所有整数引用。

## 版本兼容

### 新版游戏更新后 key 名会变化吗？

会。v4.5 → v6.6 之间，**Quest（CodexQuest）的 key 名未变**，但 **Talk 的 key 名完全变化**。每次大版本更新后需要验证 key 名是否需要适配。

### 如何检查 key 名是否变化？

```bash
# 对比新旧版本的 CodexQuest key
python -c "
import json
with open('BinOutput/CodexQuest/1000.json') as f:
    d = json.load(f)
print(list(d.keys()))
"
```

如果 key 名变化，需要更新 `src/hoyo_story/extract/base.py` 和 `src/hoyo_story/convert.py` 中的常量。

## 技术问题

### 为什么不直接用 `git clone` 全量下载？

原神全量 raw data 约 6.3 GB。sparse checkout 只下载文本相关的约 740 MB（~12%），节省磁盘空间和下载时间。

### 支持 Python 3.10 吗？

不。项目使用了一些 Python 3.11+ 特性。推荐使用 Python 3.12 或 3.13。

### 可以在 Linux/macOS 上运行吗？

可以。项目是纯 Python，跨平台支持。Windows PowerShell 克隆脚本需要自己改写为 bash 等效命令，或直接用 README 中的手动 git 命令。

### 为什么使用 `uv` 而不是 `pip`？

`uv` 是 Rust 实现的 Python 包管理器，比 pip 快 10-100 倍，且原生支持 `pyproject.toml` 的完整规范。项目配置使用 hatchling 为构建后端，`uv` 为包管理前端。
