# 运维配置指南

## 环境变量

项目通过环境变量注入 raw data 仓库地址，代码本身不硬编码任何 URL。

| 变量 | 用途 | 示例值 |
|------|------|------|
| `GENSHIN_RAW_REPO` | 原神 raw data 仓库 | `https://github.com/DimbreathBot/AnimeGameData.git` |
| `STARRAIL_RAW_REPO` | 星铁 raw data 仓库 | `https://github.com/DimbreathBot/TurnBasedGameData.git` |
| `ZZZ_RAW_REPO` | 绝区零 raw data 仓库 | `https://git.mero.moe/dimbreath/ZenlessData.git` |

### 本地使用

```bash
# Linux / macOS
export GENSHIN_RAW_REPO="https://github.com/DimbreathBot/AnimeGameData.git"

# Windows PowerShell
$env:GENSHIN_RAW_REPO = "https://github.com/DimbreathBot/AnimeGameData.git"
```

### GitHub Actions 配置

在仓库 Settings → Secrets and variables → Actions 中添加为 **Repository secrets** 或 **Variables**。

---

## GitHub Actions 定时提取

### 原神日更 Workflow（待实现）

```yaml
name: Update Genshin

on:
  schedule:
    - cron: '0 6 * * *'      # 每天 UTC 06:00
    - cron: '0 6 * * 0'      # 每周日全量刷新
  workflow_dispatch:          # 手动触发

jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Fetch raw data
        run: |
          uv run hoyo-extract fetch genshin /tmp/genshin_raw
        env:
          GENSHIN_RAW_REPO: ${{ secrets.GENSHIN_RAW_REPO }}
      - name: Extract all
        run: |
          uv run hoyo-extract pipeline genshin /tmp/genshin_raw ./output --lang CHS --type all
      - name: Commit to data archive
        run: |
          # Push to teyvat-story-archive (separate repo)
          ...
```

> ⚠️ CI runner 临时磁盘空间有限（~14 GB）。全量 clone 6.3 GB 不可行，  
> sparse checkout ~740 MB 完全可行。

---

## 数据归档仓库

提取产出的 `.txt` 推送到独立的数据归档仓库，与提取引擎分离：

| 游戏 | 数据仓库 | 状态 |
|------|------|:---:|
| 原神 | `teyvat-story-archive` | Phase 1 |
| 星铁 | `starrail-story-archive` | Phase 5 |
| 绝区零 | `zzz-story-archive` | Phase 6 |

数据仓库只包含纯 `.txt` 文件，不含任何原始游戏格式。

### 数据仓库 `.gitignore`

```gitignore
# 绝不允许进入数据仓库的格式
*.json
*.jsonl
*.bin
*.asset
*.blk
```

---

## 版本变更应对

DimbreathBot 在每次游戏版本更新后推送新数据。本项目的更新流程：

1. **监控更新**：订阅 Dimbreath 的 Patreon 或 watch `DimbreathBot/AnimeGameData`
2. **获取新数据**：`uv run hoyo-extract fetch genshin /tmp/v6.7_data`
3. **验证 key 名**：对比新旧版本的关键字段名是否变化
4. **适配代码**（如需要）：更新 `extract/genshin.py` 和 `convert.py` 中的 key 常量
5. **全量提取**：`uv run hoyo-extract pipeline genshin /tmp/v6.7_data ./prod --type all`
6. **推送产出**：`git commit && git push` 到数据归档仓库

### Key 名变化历史

| 版本 | Quest key 变化 | Talk key 变化 | 适配代码 |
|------|:---:|:---:|:---:|
| v4.5 → v6.6 | 无变化 | **全部变化** | `convert.py` 新增 TALK_A/B 常量 |
