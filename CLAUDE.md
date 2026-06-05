---
project: "hoyo-story-extractor"
branch: "main"
---

# CLAUDE.md — AI 协作者说明

`hoyo-story-extractor` 是一个多游戏的米哈游（HoYoverse）剧情文本自动提取引擎。从 [DimbreathBot](https://github.com/DimbreathBot) 的 raw datamine 数据中提取对话文本，产出纯 `.txt` 文件供下游知识库（mcp-kb）消费。

**支持游戏**（按优先级）：原神 → 星穹铁道 → 绝区零。当前处于 Phase 1：原神引擎搭建。

## 相关文档

| 想看... | 去哪里 |
|---|---|
| 架构说明 | [`docs/dev/architecture.md`](docs/dev/architecture.md) |
| 代码风格与协作规则 | [`docs/dev/style.md`](docs/dev/style.md) |
| DMCA 风险说明 | [`docs/admin/dmca.md`](docs/admin/dmca.md) |
| 本地 PoC 验证代码 | `local_dev/sandbox/`（已忽略） |
| 参考实现（Project Sekai 架构） | `ci-ke/ProjectSekai-story`（外部） |

动手写代码前先读 `docs/dev/architecture.md` 和 `docs/admin/dmca.md`。

---

## 项目架构速览

```
hoyo-story-extractor/          ← 提取引擎（本仓库，纯 Python，不含游戏数据）
├── src/hoyo_story/
│   ├── fetch.py               ← 统一的 raw data 获取（sparse checkout）
│   ├── extract/
│   │   ├── base.py            ← 公共提取逻辑（递归哈希替换等）
│   │   ├── genshin.py         ← 原神特化
│   │   ├── starrail.py        ← 星铁特化（Phase 5）
│   │   └── zzz.py             ← 绝区零特化（Phase 6）
│   └── convert.py             ← JSONL → .txt 转换
├── .github/workflows/         ← CI
└── pyproject.toml             ← uv 项目配置
```

数据仓库与本仓库分离，每个游戏一个独立 repo（纯 `.txt`，不含原始游戏文件）：
- `teyvat-story-archive`（原神）
- `starrail-story-archive`（星铁）
- `zzz-story-archive`（绝区零）

---

## 技术关键点

- **包管理**：`uv`（`pyproject.toml`），不要用 pip/poetry
- **Python**：≥3.11，类型标注不强求但鼓励在公共接口（`base.py`）中使用
- **原神文本哈希**：两套并行——`TextMap{lang}.json`（对话内容，整数 hash）+ `TextMap_Medium{lang}.json`（Speaker 名称，整数 hash）。提取时必须合并到同一个字典
- **星铁文本哈希**：xxhash 方案，单表 `TextMap{lang}.json`
- **公共逻辑不重复**：`replace_hashes()`、`to_markdown()`、sparse checkout 等放 `base.py`，各游戏子类只覆盖差异点
- **Raw data 获取**：sparse checkout，原神全量 6.3 GB → 最小集 ~250 MB
- **GitHub Actions 临时空间**：raw JSON 和中间 JSONL 只在 CI runner `/tmp` 产生，从不进入 git 仓库

## 硬性约束

- **绝不在此仓库或任何数据仓库中提交原始游戏文件**（`.json`/`.bin`/`.asset` 等来自 Dimbreath 的数据）。`.gitignore` 必须排除 `*.json`、`*.jsonl`
- **Raw data URL 不硬编码**：通过环境变量（`GENSHIN_RAW_REPO` 等）注入，代码本身只是"通用的游戏文本提取框架"
- **每个游戏的 workflow 独立**：一个游戏的提取失败不应阻塞另一个
- **产出格式**：纯 `.txt`，格式为 `角色名：台词` + 舞台指示，按 quest 分文件

---

## 启动准则

- **需明确指令才 Commit**。讨论中提到"要提交"不算指令，必须有"请提交 / 请 commit / 请开 PR"这类明确祈使句
- **一般不在 main 直接工作**。初始化阶段（Phase 1 bootstrapping）可以放宽，但 feat/fix/refactor 级一律走分支
- **不主动 push**。即使刚 commit 完，也等用户说"请推"

## 分支命名

`<type>/<topic>`，type 用 Conventional Commits 的类型。例：
- `feat/genshin-extract-quests`
- `fix/avatar-textmap-v6.6`
- `chore/ci-workflow-setup`

## 单次迭代循环

1. **对齐计划**：动手前用 1-2 段话描述打算做什么、拆成几个 commit、可能的风险。等用户点头
2. **拉分支**：按上面的命名约定
3. **动手**：按 commit 主题分批提交
4. **本地验证**：跑通提取 → 转换 → 检查产出完整性
5. **推分支 + 开 PR**（如有远程仓库）
6. **人类 merge**：等用户确认

## Commit 规范

严格遵守 [Conventional Commits](https://www.conventionalcommits.org/)。

格式：`<type>(<scope>): <subject>`

- **type**：`feat` / `fix` / `refactor` / `docs` / `chore` / `test`
- **scope** 常用：`fetch` / `extract` / `convert` / `ci` / `genshin` / `starrail` / `zzz`
- **subject** 小写、祈使、≤72 字符、无句号

```bash
git commit -m "$(cat <<'EOF'
feat(extract): implement recursive hash replacement for Genshin TextMap

Merge TextMap CHS and TextMap_MediumCHS into a single lookup table,
then recursively walk JSON trees replacing integer hashes with text.
EOF
)"
```

不使用 `--amend`（除非用户明确要求）；不加 `--no-verify`。

---

## 原神 PoC 已跑通的内容

以下在 `local_dev/sandbox/` 中已验证可用，作为 Phase 1 实现的基线：

| 步骤 | 命令/文件 | 产出 |
|---|---|---|
| Sparse clone | `git clone --depth=1 --filter=blob:none --sparse` | ~250 MB（vs 6.3 GB 全量） |
| 提取 quests | 修复版 `extract_quests.py`（合并 TextMap + 递归替换） | `quest_CHS.jsonl` (59 MB) |
| 转换 | 自写 `convert_genshin.py`（JSONL → 按 quest 分文件的 .txt） | 483 个 `.txt` (CHS 9.6 MB) |

**已知缺口**：星铁/绝区零仍是后续阶段代码桩；活动剧情数据路径未完整探索；`{NICKNAME}` 等游戏变量残留未清洗。

---

## 目录约定

| 路径 | 用途 |
|---|---|
| `src/hoyo_story/` | 提取引擎源码 |
| `local_dev/` | 本地实验脚本、PoC 代码（`.gitignore` 排除） |
| `.github/workflows/` | CI 配置 |
