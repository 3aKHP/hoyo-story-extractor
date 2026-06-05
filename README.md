# hoyo-story-extractor

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

多游戏米哈游（HoYoverse）剧情文本自动提取引擎。

从社区 datamine 数据中提取对话文本、角色故事、物品描述，产出纯 `.txt` 文件供知识库 / NLP 数据集消费。

**支持的游戏**（按优先级）：

| 游戏 | 状态 |
|------|:---:|
| 原神（Genshin Impact） | ✅ Phase 1 — 可用的 |
| 星穹铁道（Honkai: Star Rail） | ✅ Phase 5 — 可用的 |
| 绝区零（Zenless Zone Zero） | 🔜 Phase 6 |

当前公开 CLI 支持 `genshin` 和 `starrail`。绝区零模块保留为后续阶段代码桩。

---

## 快速开始

### 1. 安装

```bash
git clone https://github.com/3aKHP/hoyo-story-extractor.git
cd hoyo-story-extractor

# 需要 Python 3.11+ 和 uv
uv sync --extra dev
```

未激活虚拟环境时，请通过 `uv run hoyo-extract ...` 调用 CLI。下方示例均使用
`uv run`，这样在 Windows/macOS/Linux 上复制即可运行。

### 2. 获取游戏数据

需要先从 DimbreathBot 的 datamine 仓库 sparse clone 游戏文本数据。

**原神**（Windows PowerShell）：

```powershell
.\scripts\clone_genshin_raw.ps1 -TargetDir .\genshin_raw -Proxy http://127.0.0.1:7897
```

> GitHub 访问可能需要代理。脚本默认使用 `http://127.0.0.1:7897`，可通过 `-Proxy` 参数指定。
>
> Sparse checkout 仅下载文本相关的 ~740 MB（全量 6.3 GB）。

### 3. 提取文本

```bash
# 全部提取（任务 + 对话 + 角色 + 物品）
uv run hoyo-extract pipeline genshin ./genshin_raw ./output --lang CHS --type all

# 只提取任务剧情
uv run hoyo-extract pipeline genshin ./genshin_raw ./quests --type quests

# 分步执行
uv run hoyo-extract extract genshin ./genshin_raw --type talks -o talks.jsonl
uv run hoyo-extract convert talks.jsonl ./talks_txt --type talks
```

---

## 提取数据类型

| 类型 | 数据源 | v6.6 产出 |
|------|--------|:---:|
| **Quests** | `BinOutput/CodexQuest/*.json` | 483 个任务 |
| **Talks** | `BinOutput/Talk/` (15 子类) | 47,576 段 NPC/物件对话 |
| **Avatars** | `ExcelBinOutput/Avatar*` + `Fetter*` | 120 角色资料/语音/故事 |
| **Materials** | `ExcelBinOutput/Material*` | 9,596 材料 |
| **Weapons** | `ExcelBinOutput/Weapon*` + `Readable/` | 241 武器 |
| **Relics** | `ExcelBinOutput/Reliquary*` + `Readable/` | 4,292 圣遗物 |

---

## 架构

```
hoyo-story-extractor/              ← 提取引擎（纯 Python，不含游戏数据）
├── src/hoyo_story/
│   ├── fetch.py                   ← Raw data 获取（sparse checkout）
│   ├── extract/
│   │   ├── base.py                ← 公共提取逻辑（递归哈希替换）
│   │   ├── genshin.py             ← 原神特化（v6.6 适配）
│   │   ├── starrail.py            ← 星铁桩（Phase 5）
│   │   └── zzz.py                 ← 绝区零桩（Phase 6）
│   ├── convert.py                 ← JSONL → .txt 转换器
│   └── cli.py                     ← typer CLI（hoyo-extract）
├── scripts/
│   └── clone_genshin_raw.ps1      ← Windows sparse-clone 辅助脚本
├── tests/                         ← 45 个单元测试
├── .github/workflows/             ← CI
├── pyproject.toml
└── README.md
```

核心设计：**`fetch` 下载数据 → `extract` 递归替换哈希 → `convert` 格式化为可读文本**。  
各游戏只覆盖差异点（哈希方案、数据路径、key 名映射），公共逻辑不重复。

---

## 产出格式

### 任务剧情 (Quests)

```markdown
# 浮世浮生千岩间
*在璃月之地的海边，有一座伫立于坚岩的城市…*
> 第一章 第一幕

### 与派蒙交谈

**派蒙**：要寻找岩神的话，一年里只有这一次机会。
**旅行者**：派蒙知道具体时间吗？
```

### NPC 对话 (Talks)

```markdown
# Gadget Talk 1101926

**果核**：（一枚新鲜的果核，说明不久之前有人来过。）
**果核**：（很难看出进一步的线索了。）
```

### 角色资料 (Avatars)

```markdown
# 七七

药庐「不卜庐」的采药姑娘兼学徒。

- **神之眼**: 冰
- **命之座**: 法铃座
- **生日**: 3.3

## 语音

**初次见面…**：我是七七，是个僵尸…

## 角色故事

### 角色详细
...
```

---

## 开发

```bash
uv sync --extra dev     # 安装全部依赖
uv run pytest           # 运行测试
uv run ruff check src/ tests/  # 代码检查
uv run hoyo-extract --help     # 查看 CLI 帮助
```

---

## 数据来源声明

本项目的提取引擎本身**不包含任何游戏原始文件**。提取过程中，raw data（`.json` 等格式）仅在用户本地磁盘或 CI runner 临时存储中存在，从不进入本仓库。

数据产出的 `.txt` 文件存放于独立的数据归档仓库中。产出的对话转录类似于游戏 wiki 的任务对话页面，仅用于信息参考和研究目的。

本仓库不包含：
- 任何游戏可执行代码
- 任何游戏美术、音频或视频资产
- 任何游戏原始数据文件（JSON、二进制等）

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。

本仓库仅包含提取引擎的 Python 源代码。提取产出的文本版权归米哈游/HoYoverse 所有。
