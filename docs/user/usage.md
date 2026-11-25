# CLI 使用手册

## 命令概览

```
uv run hoyo-extract
├── fetch        — sparse checkout 游戏 raw data
├── extract      — 提取文本为 JSONL
├── convert      — JSONL → .txt 转换
└── pipeline     — extract + convert 一步完成
```

## 全局选项

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号 |
| `--help` | 查看帮助 |

## fetch — 获取游戏数据

```bash
uv run hoyo-extract fetch <game> <target_dir> [--proxy URL]
```

**参数**：
- `game`：游戏标识符（当前支持 `genshin` / `starrail`）
- `target_dir`：clone 目标目录（必须不存在）

**示例**：

```bash
uv run hoyo-extract fetch genshin ./genshin_raw --proxy http://127.0.0.1:7897
```

> ⚠️ 需要设置环境变量 `GENSHIN_RAW_REPO` 指向 raw data 仓库 URL。  
> 该命令从环境变量读取仓库地址，代码本身不硬编码任何 URL。

---

## extract — 提取文本

```bash
uv run hoyo-extract extract <game> <repo> [--lang LANG] [--type TYPE] [--output PATH]
```

**参数**：

| 参数 | 说明 | 默认值 |
|------|------|:---:|
| `game` | 游戏标识符 | （必填） |
| `repo` | raw data 目录路径 | （必填） |
| `--lang` / `-l` | 语言代码 | `CHS` |
| `--type` / `-t` | 提取类型 | `quests` |
| `--output` / `-o` | 输出路径 | 自动 |

**`--type` 可选值**：

| 值 | 提取内容 | 数据源 |
|------|------|------|
| `quests` | 任务剧情对话 | `BinOutput/CodexQuest/*.json` |
| `talks` | NPC/物件对话 | `BinOutput/Talk/` (15 子类) |
| `avatars` | 角色资料/语音/故事 | `ExcelBinOutput/Avatar*` + `Fetter*` |
| `misc` | 物品/武器/圣遗物 | `ExcelBinOutput/{Material,Weapon,Reliquary}*` |
| `all` | 以上全部 | — |

**示例**：

```bash
# 只提取任务剧情
uv run hoyo-extract extract genshin ./genshin_raw --lang CHS --type quests

# 只提取 NPC 对话
uv run hoyo-extract extract genshin ./genshin_raw --lang JP --type talks -o talks_JP.jsonl

# 全部提取
uv run hoyo-extract extract genshin ./genshin_raw --type all -o ./extracted/
```

---

## convert — JSONL 转 .txt

```bash
uv run hoyo-extract convert <input> <output_dir> [--type TYPE] [--data-version VERSION]
```

**参数**：

| 参数 | 说明 |
|------|------|
| `input` | JSONL 文件路径 (quests/talks/avatars) 或目录 (misc) |
| `output_dir` | .txt 输出目录 |
| `--type` / `-t` | 数据类型 (`quests` / `talks` / `avatars` / `misc`) |
| `--data-version` | 原神 raw data 版本（`6.6` / `6.7` / `7.0` / `7.2`），仅 `--type quests` 生效。默认自动探测 |

**示例**：

```bash
uv run hoyo-extract convert quest_CHS.jsonl ./quests_txt --type quests
uv run hoyo-extract convert quest_CHS.jsonl ./quests_txt --type quests --data-version 7.0
uv run hoyo-extract convert talks_CHS.jsonl ./talks_txt --type talks
uv run hoyo-extract convert avatars_CHS.jsonl ./avatars_txt --type avatars
```

> CodexQuest 在 6.6 使用 `IKECHKLEFFK`、7.0 使用 `EBNBLBEIFFJ` 等版本字段。
> `convert` / `pipeline` 会从 quest JSON 自动探测版本；
> 只有探测失败时才需要显式指定 `--data-version`。

7.2 的任务数据采用 `subQuests`、`textId` 等明文字段，支持自动探测。
任务标题由 `mainQuestTitle` 读取，简介和章节元信息分别保留。
Talk 的显式说话人名称优先使用；缺省的 NPC 名称从同一 raw 快照的 NPC 表补全。
角色文件名包含序号，多个同名角色记录分别保存。

---

## pipeline — 一键管道

```bash
uv run hoyo-extract pipeline <game> <repo> <output_dir> [--lang LANG] [--type TYPE] [--data-version VERSION]
```

**参数**：同 `extract` + `convert` 的合并（`--data-version` 语义同上，仅原神 quest 生效）。

`pipeline` 的 `<output_dir>` 是产品根目录：`--type all` 和单类
`--type quests` / `talks` / `avatars` 都会写入 `<output_dir>/<type>/`，
`--type misc` 会写入 `<output_dir>/misc/<category>/`。

**示例**：

```bash
# 全量提取
uv run hoyo-extract pipeline genshin ./genshin_raw ./output --lang CHS --type all

# 固定为 7.2 的数据快照，使用独立输出目录
uv run hoyo-extract pipeline genshin ./genshin_72_raw ./local_prod/genshin/v7.2 --lang CHS --type all --data-version 7.2

# 单类
uv run hoyo-extract pipeline genshin ./genshin_raw ./output --type quests
```

---

## 语言代码

常用的语言代码：

| 代码 | 语言 |
|:---:|------|
| CHS | 简体中文 |
| CHT | 繁體中文 |
| JP | 日本語 |
| EN | English |
| KR | 한국어 |

完整列表取决于 TextMap 目录中存在的文件。
